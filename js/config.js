(function () {
    "use strict";

    const direccionServidor = "http://127.0.0.1:8000";

    window.SIGNIA_CONFIG = Object.freeze({
        API_URL: direccionServidor.replace(/\/+$/, "")
    });
})();