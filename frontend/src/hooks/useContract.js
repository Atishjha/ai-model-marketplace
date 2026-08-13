import { useEffect, useState } from "react";
import { Contract } from "ethers";
import ModelRegistryAbi from "../lib/ModelRegistryAbi.json";

const CONTRACT_ADDRESS = import.meta.env.VITE_CONTRACT_ADDRESS;

/**
 * Resolves to a Contract instance connected to the current signer, or null
 * if no wallet is connected yet. Read-only marketplace data comes from the
 * backend API instead of this contract directly — see Phase 3: the indexer
 * mirrors on-chain state into Postgres for exactly this reason, so querying
 * the chain on every page load isn't necessary.
 *
 * getSigner() is itself async, so this is a stateful hook (not a plain
 * useMemo, which can't await) — it resolves once and re-resolves whenever
 * the provider changes (e.g. wallet reconnects).
 */
export function useContract(provider) {
  const [contract, setContract] = useState(null);

  useEffect(() => {
    let cancelled = false;

    if (!provider || !CONTRACT_ADDRESS) {
      setContract(null);
      return;
    }

    provider.getSigner().then((signer) => {
      if (!cancelled) {
        setContract(new Contract(CONTRACT_ADDRESS, ModelRegistryAbi, signer));
      }
    });

    return () => {
      cancelled = true;
    };
  }, [provider]);

  return contract;
}
