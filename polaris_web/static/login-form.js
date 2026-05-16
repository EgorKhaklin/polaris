/* v8.14 — Custom login validation (CSP-compliant external script).
   Replaces the browser's default "Please fill out this field" popup
   (white box + orange !) with an inline sci-fi error line.

   Required: <form class="login-form" novalidate> with two inputs
   (#username, #password) and a <div id="loginError" class="login-error">. */

(function () {
    'use strict';

    var form = document.querySelector('.login-form');
    if (!form) return;
    var err = document.getElementById('loginError');
    var u   = document.getElementById('username');
    var p   = document.getElementById('password');
    if (!err || !u || !p) return;

    function setError(msg, focusEl) {
        err.textContent = msg;
        err.classList.add('login-error-visible');
        if (focusEl) {
            focusEl.classList.add('input-invalid');
            try { focusEl.focus(); } catch (e) { /* ignore */ }
        }
    }

    function clearError() {
        err.textContent = '';
        err.classList.remove('login-error-visible');
        u.classList.remove('input-invalid');
        p.classList.remove('input-invalid');
    }

    u.addEventListener('input', clearError);
    p.addEventListener('input', clearError);

    form.addEventListener('submit', function (e) {
        clearError();
        var uv = u.value.trim();
        var pv = p.value;
        if (!uv) {
            e.preventDefault();
            setError('OPERATOR ID REQUIRED', u);
            return;
        }
        if (!/^[a-z0-9._-]{3,50}$/.test(uv)) {
            e.preventDefault();
            setError('OPERATOR ID FORMAT INVALID — 3-50 chars (a-z, 0-9, . _ -)', u);
            return;
        }
        if (!pv) {
            e.preventDefault();
            setError('CREDENTIAL REQUIRED', p);
            return;
        }
    });
})();
