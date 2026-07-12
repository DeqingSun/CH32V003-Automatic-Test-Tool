/* global Api */
const Api = (() => {
  async function request(path, options = {}) {
    const { timeout, ...rest } = options;
    const opts = { ...rest };
    opts.headers = { ...(rest.headers || {}) };
    if (opts.body && typeof opts.body === "object" && !(opts.body instanceof FormData)) {
      opts.headers["Content-Type"] = "application/json";
      opts.body = JSON.stringify(opts.body);
    }

    let timer = null;
    if (timeout != null && timeout > 0) {
      const controller = new AbortController();
      opts.signal = controller.signal;
      timer = setTimeout(() => controller.abort(), timeout);
    }

    try {
      const res = await fetch(path, opts);
      let data = null;
      const text = await res.text();
      if (text) {
        try {
          data = JSON.parse(text);
        } catch {
          data = { detail: text };
        }
      }
      if (!res.ok) {
        const detail = (data && (data.detail || data.error)) || res.statusText;
        const err = new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
        err.status = res.status;
        err.data = data;
        throw err;
      }
      return data;
    } finally {
      if (timer != null) clearTimeout(timer);
    }
  }

  function wsUrl(path) {
    const proto = location.protocol === "https:" ? "wss:" : "ws:";
    return `${proto}//${location.host}${path}`;
  }

  return {
    get: (path, options) => request(path, options || {}),
    post: (path, body, options) => request(path, { ...(options || {}), method: "POST", body }),
    upload: (path, formData, options) =>
      request(path, { ...(options || {}), method: "POST", body: formData }),
    wsUrl,
  };
})();
