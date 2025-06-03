// plik: static/js/main.js

// document.addEventListener('DOMContentLoaded', function() {
//   console.log("LoLStats JS is working properly");
// });

document.addEventListener('DOMContentLoaded', function() {
  const form = document.getElementById('search-form');
  const overlay = document.getElementById('loading-overlay');
  form.addEventListener('submit', function() {
    overlay.style.display = 'flex';
  });
});