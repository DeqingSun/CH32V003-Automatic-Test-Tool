/* global Api */
const Api = (() => {
  async function request(path, options = {}) {
    const opts = { ...options };
    opts.headers = { ...(options.headers || {}) };
    if (opts.body && typeof opts.body === "object" && !(opts.body instanceof FormData)) {
      opts.headers["Content-Type"] = "application/json";
      opts.body = JSON.stringify(opts.body);
    }
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
  }

  function wsUrl(path) {
    const proto = location.protocol === "https:" ? "wss:" : "ws:";
    return `${proto}//${location.host}${path}`;
  }

  return {
    get: (path) => request(path),
    post: (path, body) => request(path, { method: "POST", body }),
    upload: (path, formData) => request(path, { method: "POST", body: formData }),
    wsUrl,
  };
})();
