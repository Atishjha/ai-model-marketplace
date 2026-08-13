import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { formatEther } from "ethers";
import { fetchModel } from "../lib/api";
import { RatingWidget } from "../components/RatingWidget";

function truncate(str, len = 10) {
  return str && str.length > len ? `${str.slice(0, len)}…` : str;
}

function VersionChain({ versions }) {
  const sorted = [...versions].sort((a, b) => a.version_number - b.version_number);
  return (
    <div>
      {sorted.map((v, i) => (
        <div key={v.version_number} style={{ display: "flex", gap: "1em" }}>
          <div style={{ display: "flex", flexDirection: "column", alignItems: "center", width: "1.5em" }}>
            <span
              style={{
                width: "0.6em",
                height: "0.6em",
                borderRadius: "50%",
                background: i === sorted.length - 1 ? "var(--copper)" : "var(--line)",
                border: i === sorted.length - 1 ? "none" : "1px solid var(--parchment-dim)",
                flexShrink: 0,
              }}
            />
            {i < sorted.length - 1 && <div style={{ width: "1px", flex: 1, background: "var(--line)", minHeight: "2.5em" }} />}
          </div>
          <div style={{ paddingBottom: "1.5em" }}>
            <div style={{ display: "flex", alignItems: "baseline", gap: "0.75em", marginBottom: "0.2em" }}>
              <span style={{ fontFamily: "var(--face-display)", fontWeight: 600 }}>v{v.version_number}</span>
              <span className="hash" title={v.ipfs_hash}>
                {truncate(v.ipfs_hash, 18)}
              </span>
            </div>
            {v.note && <p style={{ color: "var(--parchment-dim)", margin: 0, fontSize: "0.9em" }}>{v.note}</p>}
            <span className="mono" style={{ color: "var(--parchment-dim)", fontSize: "0.75em" }}>
              {new Date(v.created_at).toLocaleDateString()}
            </span>
          </div>
        </div>
      ))}
    </div>
  );
}

export function ModelDetail({ contract, walletAddress }) {
  const { modelId } = useParams();
  const [model, setModel] = useState(null);
  const [hasLicense, setHasLicense] = useState(false);
  const [purchasing, setPurchasing] = useState(false);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchModel(modelId)
      .then(setModel)
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, [modelId]);

  useEffect(() => {
    // hasLicense() is keyed by the contract's on_chain_id, not our DB row id —
    // model.on_chain_id is what the deployed contract actually knows about.
    if (!contract || !walletAddress || !model) return;
    contract.hasLicense(model.on_chain_id, walletAddress).then(setHasLicense).catch(() => {});
  }, [contract, walletAddress, model]);

  const purchase = async () => {
    if (!contract || !model) return;
    setPurchasing(true);
    setError(null);
    try {
      const tx = await contract.purchaseLicense(model.on_chain_id, { value: model.price_wei.toString() });
      await tx.wait();
      setHasLicense(true);
    } catch (err) {
      setError(err?.reason || err?.message || "Purchase failed");
    } finally {
      setPurchasing(false);
    }
  };

  if (loading) return <p className="mono" style={{ color: "var(--parchment-dim)" }}>loading…</p>;
  if (error && !model) return <p style={{ color: "var(--danger)" }}>{error}</p>;
  if (!model) return null;

  const priceLabel = Number(model.price_wei) === 0 ? "free" : `${formatEther(model.price_wei.toString())} MATIC`;
  const ratingCount = model.rating_count ?? 0;

  return (
    <div style={{ maxWidth: "640px" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "0.3em" }}>
        <h1 style={{ fontSize: "1.8em" }}>{model.name || "untitled model"}</h1>
        <span className="badge">{model.license_type}</span>
      </div>
      <p className="hash" style={{ marginBottom: "1.5em" }}>owner {model.owner_address}</p>
      {model.description && <p style={{ color: "var(--parchment-dim)", marginBottom: "1.5em" }}>{model.description}</p>}

      <div className="card" style={{ padding: "1.25em", marginBottom: "2em", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <div>
          <div style={{ fontFamily: "var(--face-display)", fontSize: "1.4em", color: "var(--copper-bright)" }}>{priceLabel}</div>
          {ratingCount > 0 && (
            <div className="mono" style={{ color: "var(--parchment-dim)", fontSize: "0.85em" }}>
              {model.avg_rating.toFixed(1)} avg · {ratingCount} rating{ratingCount !== 1 ? "s" : ""}
            </div>
          )}
        </div>

        {hasLicense ? (
          <span className="badge">✓ licensed</span>
        ) : (
          <button className="btn btn-primary" onClick={purchase} disabled={purchasing || !contract}>
            {purchasing ? "Confirming…" : "Buy license"}
          </button>
        )}
      </div>

      {error && (
        <p style={{ color: "var(--danger)", marginBottom: "1.5em" }}>{error}</p>
      )}

      <section style={{ marginBottom: "2em" }}>
        <h2 style={{ fontSize: "1.1em", marginBottom: "1em", color: "var(--parchment-dim)", textTransform: "uppercase", letterSpacing: "0.08em", fontFamily: "var(--face-mono)" }}>
          Version history
        </h2>
        <VersionChain versions={model.versions} />
      </section>

      <section>
        <h2 style={{ fontSize: "1.1em", marginBottom: "0.75em", color: "var(--parchment-dim)", textTransform: "uppercase", letterSpacing: "0.08em", fontFamily: "var(--face-mono)" }}>
          Rate this model
        </h2>
        <RatingWidget contract={contract} modelId={model.on_chain_id} hasLicense={hasLicense} />
      </section>
    </div>
  );
}
