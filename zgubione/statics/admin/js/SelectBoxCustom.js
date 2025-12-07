/*
Custom Select Box, which needs 2 cache objects for operations of addition and deletion of item in single
multiple select box
*/
(function($) {
  'use strict';
  var SelectBoxCustom = {
    cache_prev: {},
    cache_to: {},
    init: function(id) {
      var box = document.getElementById(id);
      var node;
      SelectBoxCustom.cache_prev[id] = [];
      SelectBoxCustom.cache_to[id] = [];
      var cache_prev = SelectBoxCustom.cache_prev[id];
      var cache_to = SelectBoxCustom.cache_to[id];
      var boxOptions = box.options;
      var boxOptionsLength = boxOptions.length;
      for (var i = 0, j = boxOptionsLength; i < j; i++) {
        node = boxOptions[i];
        cache_prev.push({value: node.value, text: node.text, displayed: 1});
        cache_to.push({value: node.value, text: node.text, displayed: 1});
      }
    },
    redisplay: function(id) {
      // Repopulate HTML select box from cache
      var box = document.getElementById(id);
      var node;
      $(box).empty(); // clear all options
      var new_options = box.outerHTML.slice(0, -9);  // grab just the opening tag
      var cache = SelectBoxCustom.cache_to[id];
      for (var i = 0, j = cache.length; i < j; i++) {
        node = cache[i];
        if (node.displayed) {
          var new_option = new Option(node.text, node.value, false, false);
          // Shows a tooltip when hovering over the option
          new_option.setAttribute("title", node.text);
          new_options += new_option.outerHTML;
        }
      }
      new_options += '</select>';
      box.outerHTML = new_options;
    },
    delete_from_cache: function(id, value, direction) {
      var node, delete_index = null;
      var cache = SelectBoxCustom['cache_' + direction][id];
      for (var i = 0, j = cache.length; i < j; i++) {
        node = cache[i];
        if (node.value === value) {
          delete_index = i;
          break;
        }
      }
      cache.splice(delete_index, 1);
    },
    add_to_cache: function(id, option, direction) {
      SelectBoxCustom['cache_' + direction][id].push({value: option.value, text: option.text, displayed: 1});
    },
    cache_contains: function(id, value, direction) {
      console.log('cache contains')
      // Check if an item is contained in the cache
      var node;
      console.log('cache_' + direction)
      var cache = SelectBoxCustom['cache_' + direction][id];
      console.log(cache);
      for (var i = 0, j = cache.length; i < j; i++) {
        node = cache[i];
        if (node.value === value) {
          return true;
        }
      }
      return false;
    }
  };
  window.SelectBoxCustom = SelectBoxCustom;
})(django.jQuery);
