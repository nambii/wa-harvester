function(doc) {
  if (doc.website != null) {
    if (doc.website.sitemap != null) {
      if( Object.prototype.toString.call( doc.website.sitemap ) === '[object Array]' ) {
        for (var i = 0; i < doc.website.sitemap.length; i++) {
          emit(doc.website.sitemap[i], doc._id);
        }
      } else {
        emit(doc.website.sitemap, doc._id);
      }
    }
    if (doc.website.rss != null) {
      if( Object.prototype.toString.call( doc.website.rss ) === '[object Array]' ) {
        for (var i = 0; i < doc.website.rss.length; i++) {
          emit(doc.website.rss[i], doc._id);
        }
      } else {
        emit(doc.website.rss, doc._id);
      }
    }
  }
  if (doc.podcast != null) {
    if (doc.podcast.rss != null) {
      if( Object.prototype.toString.call( doc.podcast.rss ) === '[object Array]' ) {
        for (var i = 0; i < doc.podcast.rss.length; i++) {
          emit(doc.podcast.rss[i], doc._id);
        }
      } else {
        emit(doc.podcast.rss, doc._id);
      }
    }
  }
}

// if( Object.prototype.toString.call( doc.facebook ) === '[object Object]' )
//
// function lol(param) {
//   if( Object.prototype.toString.call( param ) === '[object Array]' ) {
//     return param[0];
//   }
//   else {
//     return param;
//   }
// }
