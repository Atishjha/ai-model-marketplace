import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { parseEther } from "ethers";
import { uploadModelFile, waitForIndexedModel } from "../lib/api";

const LICENSE_OPTIONS = ["MIT", "commercial-single-use", "royalty-5pct"];

export function Publish({ contract, walletAddress }) {
  const navigate = useNavigate();
  const [name, setName] = useState("");
  const [licenseType, setLicenseType] = useState(LICENSE_OPTIONS[0]);
  const [priceMatic, setPriceMatic] = useState("0");
  const [file, setFile] = useState(null);

  const [stage, setStage] = useState("idle"); // idle | uploading | registering | done
  const [progress, setProgress] = useState(0);
  const [error, setError] = useState(null);

  const submit = async (e) => {
    e.preventDefault();
    if (!contract) {
      setError("Connect your wallet first.");
      return;
    }
    if (!file) {
      setError("Choose a model file to publish.");
      return;
    }

    setError(null);
    try {
      setStage("uploading");
      setProgress(0);
      const cid = await uploadModelFile(file, setProgress);

      setStage("registering");
      const priceWei = parseEther(priceMatic || "0");
      const tx = await contract.registerModel(name, cid, priceWei, licenseType);
      await tx.wait();

      setStage("indexing");
      // The transaction is confirmed on-chain, but the marketplace listing
      // reads from Postgres, and the indexer's own on_chain_id != the DB row
      // id the detail route uses — so we can't build that URL from the
      // receipt alone. Poll by owner+name for the row the indexer creates.
      const indexed = await waitForIndexedModel(walletAddress, name);

      setStage("done");
      setTimeout(() => navigate(indexed ? `/models/${indexed.id}` : "/"), indexed ? 500 : 0);
    } catch (err) {
      setError(err?.reason || err?.message || "Publish failed");
      setStage("idle");
    }
  };

  const busy = stage === "uploading" || stage === "registering" || stage === "indexing";

  return (
    <div style={{ maxWidth: "520px" }}>
      <h1 style={{ fontSize: "1.8em", marginBottom: "0.3em" }}>Publish a model</h1>
      <p style={{ color: "var(--parchment-dim)", marginBottom: "2em" }}>
        The file goes straight to IPFS from your browser. Registration is a transaction you'll confirm in your wallet.
      </p>

      {!walletAddress && (
        <p className="badge" style={{ color: "var(--danger)", borderColor: "rgba(201,106,90,0.4)", marginBottom: "1.5em" }}>
          connect a wallet to publish
        </p>
      )}

      <form onSubmit={submit} style={{ display: "flex", flexDirection: "column", gap: "1.25em" }}>
        <label style={fieldStyle}>
          <span style={labelStyle}>Model name</span>
          <input
            required
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="SentimentNet"
            style={inputStyle}
            disabled={busy}
          />
        </label>

        <label style={fieldStyle}>
          <span style={labelStyle}>Model file</span>
          <input
            required
            type="file"
            onChange={(e) => setFile(e.target.files?.[0] ?? null)}
            style={{ ...inputStyle, padding: "0.5em" }}
            disabled={busy}
          />
        </label>

        <div style={{ display: "flex", gap: "1em" }}>
          <label style={{ ...fieldStyle, flex: 1 }}>
            <span style={labelStyle}>License</span>
            <select value={licenseType} onChange={(e) => setLicenseType(e.target.value)} style={inputStyle} disabled={busy}>
              {LICENSE_OPTIONS.map((opt) => (
                <option key={opt} value={opt}>{opt}</option>
              ))}
            </select>
          </label>

          <label style={{ ...fieldStyle, flex: 1 }}>
            <span style={labelStyle}>Price (MATIC, 0 = free)</span>
            <input
              type="number"
              min="0"
              step="0.001"
              value={priceMatic}
              onChange={(e) => setPriceMatic(e.target.value)}
              style={inputStyle}
              disabled={busy}
            />
          </label>
        </div>

        {stage === "uploading" && (
          <div>
            <div className="mono" style={{ fontSize: "0.8em", color: "var(--parchment-dim)", marginBottom: "0.4em" }}>
              uploading to IPFS — {Math.round(progress * 100)}%
            </div>
            <div style={{ height: "3px", background: "var(--line)", borderRadius: "2px", overflow: "hidden" }}>
              <div style={{ height: "100%", width: `${progress * 100}%`, background: "var(--copper)", transition: "width 0.15s ease" }} />
            </div>
          </div>
        )}
        {stage === "registering" && (
          <p className="mono" style={{ fontSize: "0.8em", color: "var(--parchment-dim)" }}>
            confirm the registration in your wallet…
          </p>
        )}
        {stage === "indexing" && (
          <p className="mono" style={{ fontSize: "0.8em", color: "var(--parchment-dim)" }}>
            confirmed on-chain — waiting for the indexer to pick it up…
          </p>
        )}
        {stage === "done" && (
          <p className="badge">✓ registered on-chain</p>
        )}
        {error && <p style={{ color: "var(--danger)" }}>{error}</p>}

        <button type="submit" className="btn btn-primary" disabled={busy || !walletAddress} style={{ alignSelf: "flex-start" }}>
          {busy ? "Publishing…" : "Publish model"}
        </button>
      </form>
    </div>
  );
}

const fieldStyle = { display: "flex", flexDirection: "column", gap: "0.4em" };
const labelStyle = { fontFamily: "var(--face-mono)", fontSize: "0.75em", color: "var(--parchment-dim)", textTransform: "uppercase", letterSpacing: "0.06em" };
const inputStyle = {
  padding: "0.65em 0.85em",
  background: "var(--ink-800)",
  border: "1px solid var(--line)",
  borderRadius: "3px",
  color: "var(--parchment)",
  fontFamily: "inherit",
  fontSize: "0.95em",
};
