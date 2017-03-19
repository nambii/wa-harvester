#!/usr/bin/python3
"""
"""

import os
import io
import string
import time
import re
import math
import collections
import itertools
import requests
import zipfile
from csv import DictReader

import pickle

import nltk
import nltk.classify.util
import nltk.metrics
from nltk.metrics import BigramAssocMeasures
from nltk.probability import FreqDist, ConditionalFreqDist
from nltk.corpus import stopwords
from nltk.classify.scikitlearn import SklearnClassifier
from sklearn.naive_bayes import BernoulliNB
from sklearn.linear_model import LogisticRegression

#sys.path.append(os.path.abspath("/home/ubuntu/wa-twitter/harvester/"))


class SentimentAnalyser():
    """
    Public attributes:
    -- _best_words:
    -- _stop_words
    -- ME_classifier
    -- BerNB_classifier
    -- LR_classifier

    pos_tweets and neg_tweets are only needed up until generate_classifiers

    Todo:
      * Delete training set CSV once we're done with it.
    """

    def __init__(self):
        """"""
        self._stop_words = self._get_stop_words()
        self._load_pickle_files()

    def _get_stop_words(self):
        punctuation = list(string.punctuation)
        stop_words = stopwords.words('english') + punctuation + ['AT_USER','URL','rt']
        return stop_words

    def _load_pickle_files(self):
        """Loads the pickle files.
        """

        # Save current working directory
        cwd = os.getcwd()
        # Change dir to where sentiment_analysis.py is located
        dir_path = os.path.dirname(os.path.realpath(__file__))
        os.chdir(dir_path)

        self._best_words = self._load_pickle_file('bestwords.pickle')
        self.ME_classifier = self._load_pickle_file('MaximumEntropy_classifier.pickle')
        self.BerNB_classifier = self._load_pickle_file('BernoulliNB_classifier.pickle')
        self.LR_classifier = self._load_pickle_file('LogisticRegression_classifier.pickle')

        # Change back to current working directory
        os.chdir(cwd)

    def _load_pickle_file(self, filename):
        """This method does not handle exceptions when (a) loading the pickle
        files fail, and (b) the download fails.
        """
        try:
            with open(filename, 'rb') as f:
                return pickle.load(f)
        except:
            url_bucket = "https://swift.rc.nectar.org.au:8888/v1/AUTH_38e73f77f1174084b27c6327aeb9590c/wa-classifiers/"
            r = requests.get(url_bucket + filename)
            with open(filename, 'wb') as f:
                f.write(r.content)
            return pickle.loads(r.content)

    def analyse(self, tweet_text):
        """"""
        processed_tweet = self._process_tweet(tweet_text)

        feature_vector = self._get_feature_vector(processed_tweet)
        feature_vector_best = self._best_word_features(feature_vector)

        dist = self.ME_classifier.prob_classify(feature_vector_best)
        ME_prob_pos = dist.prob("pos")
        ME_prob_neg = dist.prob("neg")

        dist = self.BerNB_classifier.prob_classify(feature_vector_best)
        BerNB_prob_pos = dist.prob("pos")
        BerNB_prob_neg = dist.prob("neg")

        dist = self.LR_classifier.prob_classify(feature_vector_best)
        LR_prob_pos = dist.prob("pos")
        LR_prob_neg = dist.prob("neg")

        prob_pos = (ME_prob_pos + BerNB_prob_pos + LR_prob_pos)/3
        prob_neg = (ME_prob_neg + BerNB_prob_neg + LR_prob_neg)/3

        if(prob_pos > 0.7):
            sentiment = 'positive'
        elif (prob_neg > 0.7):
    	    sentiment = 'negative'
        else:
    	    sentiment = 'neutral'

        sentiment_dict = {
            'features': list(feature_vector_best.keys()),
            'sentiment': sentiment,
            'positive_probability': prob_pos,
            'negative_probability': prob_neg
        }
        return_dict = {
            'sentiment': sentiment_dict,
            'features': feature_vector
        }
        return return_dict

    def _process_tweet(self, tweet):
        # Convert to lower case
        tweet = tweet.lower()
        # Convert www.* or https?://* to URL
        tweet = re.sub('((www\.[^\s]+)|(https?://[^\s]+))','URL',tweet)
        # Convert @username to AT_USER
        tweet = re.sub('@[^\s]+','AT_USER',tweet)
        # Remove additional white spaces
        tweet = re.sub('[\s]+', ' ', tweet)
        # Replace #hashtag with word
        tweet = re.sub(r'#([^\s]+)', r'\1', tweet)
        # Trim
        tweet = tweet.strip('\'"')
        return tweet

    def _get_feature_vector(self, tweet):
        feature_vector = []
        # Split tweet text into words
        words = tweet.split()

        for w in words:
            # Replace two or more with two occurrences
            pattern = re.compile(r"(.)\1{1,}", re.DOTALL)
            w = pattern.sub(r"\1\1", w)
            # Strip punctuation
            w = w.strip('\'"?,.')
            # Check if the word starts with an alphabet
            val = re.search(r"^[a-zA-Z][a-zA-Z0-9]*$", w)
    	    # Ignore if it is a stop word
            if (w in self._stop_words or val is None):
                continue
            else:
                feature_vector.append(w.lower())
        return feature_vector

    def _best_word_features(self, words):
        return dict([(word, True) for word in words if word in self._best_words])
        # To use all the extraction features with optimisation
        # return dict([(word, True) for word in words])



    ##### Training methods #####

    def _train(self):
        """"""
        download_sentiment_training_dataset()
        self._best_words, self.pos_tweets, self.neg_tweets = getbest_words()

        # Save current working directory
        cwd = os.getcwd()
        # Change dir to where sentiment_analysis.py is located
        dir_path = os.path.dirname(os.path.realpath(__file__))
        os.chdir(dir_path)

        with open('bestwords.pickle', 'wb') as f:
            pickle.dump(self._best_words, f)
        generate_classifiers(self.pos_tweets, self.neg_tweets)

        # Change back to current working directory
        os.chdir(cwd)

    def feature_Extraction(self, feature_select, pos_tweets, neg_tweets):
        negfeats=[]
        posfeats=[]
        for twe in neg_tweets:
            processedTweet = _process_tweet(twe)
            negfeats.append((feature_select(_get_feature_vector(processedTweet)), 'neg'))

        for twe in pos_tweets:
            processedTweet = _process_tweet(twe)
            posfeats.append((feature_select(_get_feature_vector(processedTweet)), 'pos'))
        return posfeats, negfeats

    def train_Classifier(self, posfeats, negfeats, index):
        """The training set percentage should be passed as an argument.
        """

        # divide dataset into train and validation sets
        posCutoff = int(math.floor(len(posfeats)*7/10))
        negCutoff = int(math.floor(len(negfeats)*7/10))
        trainFeatures = posfeats[:posCutoff] + negfeats[:negCutoff]
        testFeatures = posfeats[posCutoff:] + negfeats[negCutoff:]

        referenceSets = collections.defaultdict(set)
        testSets = collections.defaultdict(set)

        classsifiername=''

        if (index == 0):
            classifier = nltk.classify.maxent.MaxentClassifier.train(trainFeatures, 'GIS', trace=3, encoding=None, labels=None, gaussian_prior_sigma=0, max_iter = 5)
            classsifiername= 'Maximum Entropy'
        elif (index ==1):
            classifier = SklearnClassifier(BernoulliNB())
            classifier.train(trainFeatures)
            classsifiername='Bernoulli Naive Bayes'
        else:
            classifier = SklearnClassifier(LogisticRegression())
            classifier.train(trainFeatures)
            classsifiername = 'LogisticRegression'

        for i, (features, label) in enumerate(testFeatures):
            referenceSets[label].add(i)
            predicted = classifier.classify(features)
            testSets[predicted].add(i)
        #
        # print 'train on %d instances, test on %d instances' % (len(trainFeatures), len(testFeatures))
        # print 'accuracy:', nltk.classify.util.accuracy(classifier, testFeatures)
        # print 'pos precision:', nltk.metrics.precision(referenceSets['pos'], testSets['pos'])
        # print 'pos recall:', nltk.metrics.recall(referenceSets['pos'], testSets['pos'])
        # print 'neg precision:', nltk.metrics.precision(referenceSets['neg'], testSets['neg'])
        # print 'neg recall:', nltk.metrics.recall(referenceSets['neg'], testSets['neg'])
        #classifier.show_most_informative_features(10)
        return classifier

    def generate_classifiers(self, pos_tweets, neg_tweets):
        """"""
        start = time.clock()
        posfeats, negfeats = feature_Extraction(_best_word_features,pos_tweets,neg_tweets)

        classifier_names = [ 'MaximumEntropy_classifier','BernoulliNB_classifier','LogisticRegression_classifier']
        index=0
        for name in classifier_names:
            classifier= train_Classifier(posfeats,negfeats,index)
            index=index+1
            f = open(name+'.pickle', 'wb')
            pickle.dump(classifier, f)
            f.close()

        endT = time.clock()
        elapsed = endT - start
        print ("Time spent in Twitter Sentiment Analysis (Preprocessing + Training 3 classifiers) is: " + str(elapsed))

    def download_sentiment_training_dataset(self):
        url = 'http://thinknook.com/wp-content/uploads/2012/09/Sentiment-Analysis-Dataset.zip'

        r = requests.get(url)
        z = zipfile.ZipFile(io.BytesIO(r.content))
        z.extractall()

    def getbest_words(self):
        print ("Loading Tweets Dataset")
        pos_tweets,neg_tweets = readDataset('Sentiment Analysis Dataset.csv')

        word_scores= create_word_scores(pos_tweets,neg_tweets)

        num = 25000
        print("Evaluating best " + str(num) + " word features.")
        best_words = feature_Selection(word_scores, num)

        return best_words, pos_tweets, neg_tweets

    def readDataset(self, csv_file):
        pos_tweets=[]
        neg_tweets=[]
        senti=[]
        tweets_samples=[]
        #csv_file='Sentiment Analysis Dataset.csv'
        with open(csv_file) as f:
            for row in DictReader(f):
                label= int(row["Sentiment"])
                senti.append(label)
                tweets_samples.append(row["SentimentText"])
                if label ==0:
                    neg_tweets.append(row["SentimentText"])
                else:
                    pos_tweets.append(row["SentimentText"])
        #print pos_tweets
        #f = open('postweets.pickle', 'wb')
        #pickle.dump(pos_tweets, f)
        #f.close()

        #f = open('negtweets.pickle', 'wb')
        #pickle.dump(neg_tweets, f)
        #f.close()
        return pos_tweets,neg_tweets

    def create_word_scores(self, pos_tweets, neg_tweets):
        """"""
        posWords = []
        negWords = []
        for twe in neg_tweets:
            processedTweet = processTweet(twe)
            negWords.append(_get_feature_vector(processedTweet))

        for twe in pos_tweets:
            processedTweet = processTweet(twe)
            posWords.append(_get_feature_vector(processedTweet))

        posWords = list(itertools.chain(*posWords))
        negWords = list(itertools.chain(*negWords))

        word_fd = FreqDist()
        cond_word_fd = ConditionalFreqDist()

        for word in posWords:
            w= word.lower()
            word_fd[w]=word_fd[w]+1;
            cond_word_fd['pos'][w]=cond_word_fd['pos'][w]+1
        for word in negWords:
            w=word.lower()
            word_fd[w]= word_fd[w]+1
            cond_word_fd['neg'][w]= cond_word_fd['neg'][w]+1

        pos_word_count = cond_word_fd['pos'].N()
        neg_word_count = cond_word_fd['neg'].N()
        total_word_count = pos_word_count + neg_word_count

        word_scores = {}
        for word, freq in word_fd.items():
            pos_score = BigramAssocMeasures.chi_sq(cond_word_fd['pos'][word], (freq, pos_word_count), total_word_count)
            neg_score = BigramAssocMeasures.chi_sq(cond_word_fd['neg'][word], (freq, neg_word_count), total_word_count)
            word_scores[word] = pos_score + neg_score
        return word_scores

    def feature_Selection(self, word_scores, number):
        """rename this to find_best_words"""

        best_vals = sorted(word_scores.items(), key=lambda w_s: w_s[1], reverse=True)[:number]
        best_words = set([w for w, s in best_vals])
        return best_words

#sentiment_analyser = SentimentAnalyser()
#sentiment_analyser.get_tweet_sentiment("This is a really happy, positive tweet!!")
#sentiment_analyser.get_tweet_sentiment("This is a really sad tweet")
