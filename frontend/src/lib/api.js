const API_BASE = import.meta.env.VITE_API_URL ?? "";

async function handleResponse(res) {
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || `Request failed (${res.status})`);
  }
  return res.json();
}

/**
 * Returns the backend's paginated envelope directly: { items, total, page, page_size }.
 * Callers that just want the array should read `.items`.
 */
export async function fetchModels({ search, licenseType, ownerAddress, sort, page = 1, pageSize = 20 } = {}) {
  const params = new URLSearchParams();
  if (search) params.set("q", search);
  if (licenseType) params.set("license_type", licenseType);
  if (ownerAddress) params.set("owner_address", ownerAddress);
  if (sort) params.set("sort", sort);
  params.set("page", page);
  params.set("page_size", pageSize);

  const res = await fetch(`${API_BASE}/models?${params}`);
  return handleResponse(res);
}

export async function fetchModel(modelId) {
  const res = await fetch(`${API_BASE}/models/${modelId}`);
  return handleResponse(res);
}

/**
 * After a successful on-chain registerModel() call, the indexer needs a poll
 * cycle to create the corresponding row — and the row's DB id (what detail
 * lookups use) isn't the same as the on-chain modelId, so we can't just
 * navigate there directly. Poll by owner+name instead of guessing an id.
 */
export async function waitForIndexedModel(ownerAddress, name, { retries = 8, delayMs = 1500 } = {}) {
  for (let i = 0; i < retries; i++) {
    const { items } = await fetchModels({ ownerAddress, sort: "newest", pageSize: 5 });
    const match = items.find((m) => m.name === name);
    if (match) return match;
    await new Promise((resolve) => setTimeout(resolve, delayMs));
  }
  return null;
}

/**
 * Direct-to-IPFS upload: backend mints a short-lived signed URL, the file
 * uploads straight to Pinata from the browser (bytes never touch our
 * server), and the CID comes back for use in registerModel() on-chain.
 */
export async function uploadModelFile(file, onProgress) {
  const signRes = await fetch(`${API_BASE}/upload/signed-url`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ filename: file.name, content_type: file.type || "application/octet-stream" }),
  });
  const { url } = await handleResponse(signRes);

  const formData = new FormData();
  formData.append("file", file);
  formData.append("network", "public");

  const pinResult = await new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open("POST", url);
    xhr.upload.onprogress = (e) => {
      if (onProgress && e.lengthComputable) onProgress(e.loaded / e.total);
    };
    xhr.onload = () => {
      if (xhr.status >= 200 && xhr.status < 300) resolve(JSON.parse(xhr.responseText));
      else reject(new Error(`IPFS upload failed (${xhr.status})`));
    };
    xhr.onerror = () => reject(new Error("IPFS upload failed — network error"));
    xhr.send(formData);
  });

  const cid = pinResult?.data?.cid;
  if (!cid) throw new Error("Upload succeeded but no CID was returned");
  return cid;
}
