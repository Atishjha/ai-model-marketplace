import { Link } from "react-router-dom";
import { formatEther } from "ethers";

function truncate(address) {
  return address ? `${address.slice(0, 6)}…${address.slice(-4)}` : "";
}

function Stars({ rating }) {
  const full = Math.round(rating);
  return (
    <span className="mono" style={{ color: "var(--copper)", letterSpacing: "0.05em" }} aria-label={`${rating} out of 5`}>
      {"●".repeat(full)}
      <span style={{ color: "var(--line)" }}>{"●".repeat(5 - full)}</span>
    </span>
  );
}

export function ModelCard({ model }) {
  const priceLabel = Number(model.price_wei) === 0 ? "free" : `${formatEther(model.price_wei.toString())} MATIC`;
  const ratingCount = model.rating_count ?? 0;

  return (
    <Link
      to={`/models/${model.id}`}
      className="card"
      style={{
        display: "block",
        padding: "1.25em",
        textDecoration: "none",
        color: "inherit",
        transition: "border-color 0.15s ease, transform 0.1s ease",
      }}
      onMouseEnter={(e) => (e.currentTarget.style.borderColor = "var(--copper)")}
      onMouseLeave={(e) => (e.currentTarget.style.borderColor = "var(--line)")}
    >
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", marginBottom: "0.6em" }}>
        <h3 style={{ fontSize: "1.1em" }}>{model.name || "untitled model"}</h3>
        <span className="badge">{model.license_type}</span>
      </div>

      <div className="hash" style={{ marginBottom: "1em" }}>
        by {truncate(model.owner_address)}
      </div>

      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <span style={{ fontFamily: "var(--face-display)", fontSize: "1em", color: "var(--copper-bright)" }}>
          {priceLabel}
        </span>
        {ratingCount > 0 ? (
          <Stars rating={model.avg_rating ?? 0} />
        ) : (
          <span className="mono" style={{ color: "var(--parchment-dim)", fontSize: "0.8em" }}>
            unrated
          </span>
        )}
      </div>
    </Link>
  );
}
