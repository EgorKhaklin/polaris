/* v8.14 — Auto-dismiss flash messages after ~4.5s (CSP-compliant).
   CSS animations are unreliable under prefers-reduced-motion; this JS
   actually removes the .flash element from the DOM after the dismiss
   period so its space collapses cleanly. */

(function () {
    'use strict';

    var DISMISS_MS = 4500;
    var FADE_MS    = 600;

    var flashes = document.querySelectorAll('.flash');
    flashes.forEach(function (el) {
        setTimeout(function () {
            el.style.transition =
                'opacity ' + FADE_MS + 'ms ease, ' +
                'max-height ' + FADE_MS + 'ms ease, ' +
                'margin ' + FADE_MS + 'ms ease, ' +
                'padding ' + FADE_MS + 'ms ease, ' +
                'border-width ' + FADE_MS + 'ms ease';
            // Capture current height before collapsing
            el.style.maxHeight = el.offsetHeight + 'px';
            el.style.opacity = '0';
            requestAnimationFrame(function () {
                el.style.maxHeight   = '0px';
                el.style.paddingTop  = '0';
                el.style.paddingBottom = '0';
                el.style.marginTop   = '0';
                el.style.marginBottom = '0';
                el.style.borderWidth = '0';
            });
            setTimeout(function () { el.remove(); }, FADE_MS + 50);
        }, DISMISS_MS);
    });
})();
