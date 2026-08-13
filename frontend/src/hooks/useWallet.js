import { useCallback, useEffect, useState } from "react";
import { BrowserProvider } from "ethers";

const AMOY_CHAIN_ID = "0x13882"; // 80002 in hex — Polygon Amoy testnet

export function useWallet() {
  const [address, setAddress] = useState(null);
  const [provider, setProvider] = useState(null);
  const [chainId, setChainId] = useState(null);
  const [connecting, setConnecting] = useState(false);
  const [error, setError] = useState(null);

  const connect = useCallback(async () => {
    if (!window.ethereum) {
      setError("No wallet found. Install MetaMask to publish or buy models.");
      return;
    }
    setConnecting(true);
    setError(null);
    try {
      const browserProvider = new BrowserProvider(window.ethereum);
      const accounts = await browserProvider.send("eth_requestAccounts", []);
      const network = await browserProvider.getNetwork();

      setProvider(browserProvider);
      setAddress(accounts[0]);
      setChainId("0x" + network.chainId.toString(16));

      if ("0x" + network.chainId.toString(16) !== AMOY_CHAIN_ID) {
        setError("Wrong network — switch your wallet to Polygon Amoy testnet.");
      }
    } catch (err) {
      setError(err?.message ?? "Connection was rejected");
    } finally {
      setConnecting(false);
    }
  }, []);

  const disconnect = useCallback(() => {
    setAddress(null);
    setProvider(null);
    setChainId(null);
  }, []);

  // Keep in sync if the user switches accounts/networks from inside the wallet
  useEffect(() => {
    if (!window.ethereum) return;

    const handleAccountsChanged = (accounts) => {
      if (accounts.length === 0) disconnect();
      else setAddress(accounts[0]);
    };
    const handleChainChanged = (newChainId) => {
      setChainId(newChainId);
      setError(newChainId !== AMOY_CHAIN_ID ? "Wrong network — switch to Polygon Amoy testnet." : null);
    };

    window.ethereum.on("accountsChanged", handleAccountsChanged);
    window.ethereum.on("chainChanged", handleChainChanged);
    return () => {
      window.ethereum.removeListener("accountsChanged", handleAccountsChanged);
      window.ethereum.removeListener("chainChanged", handleChainChanged);
    };
  }, [disconnect]);

  return {
    address,
    provider,
    chainId,
    isCorrectNetwork: chainId === AMOY_CHAIN_ID,
    connecting,
    error,
    connect,
    disconnect,
  };
}
