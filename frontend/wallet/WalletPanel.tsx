import { useState } from "react";
import { BrowserProvider, Contract, keccak256, toUtf8Bytes } from "ethers";

import { resolutionStorageAbi } from "../lib/contracts";
import { useSession } from "../lib/session";

const resolutionStorageAddress = import.meta.env.VITE_RESOLUTION_STORAGE_ADDRESS as
  | string
  | undefined;

export function WalletPanel() {
  const { result } = useSession();
  const [address, setAddress] = useState<string | null>(null);
  const [txHash, setTxHash] = useState<string | null>(null);
  const [status, setStatus] = useState<string>("Wallet not connected.");
  const [isConnecting, setIsConnecting] = useState(false);
  const [isWriting, setIsWriting] = useState(false);
  const isConnected = Boolean(address);

  const metadataHash = result
    ? keccak256(toUtf8Bytes(result.storage_payload.canonical_json))
    : null;

  async function handleConnect() {
    if (!window.ethereum) {
      setStatus("No injected wallet found. Install MetaMask or another EIP-1193 wallet.");
      return;
    }

    setIsConnecting(true);
    try {
      const accounts = (await window.ethereum.request({
        method: "eth_requestAccounts",
      })) as string[];
      setAddress(accounts[0] ?? null);
      setStatus("Wallet connected.");
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Wallet connection failed.");
    } finally {
      setIsConnecting(false);
    }
  }

  function handleDisconnect() {
    setAddress(null);
    setTxHash(null);
    setStatus("Wallet disconnected locally.");
  }

  async function handleStoreResolution() {
    if (!result || !resolutionStorageAddress || !metadataHash) {
      setStatus("Missing result, contract address, or metadata hash.");
      return;
    }

    if (!window.ethereum) {
      setStatus("No injected wallet found for contract write.");
      return;
    }

    setIsWriting(true);
    try {
      const provider = new BrowserProvider(window.ethereum);
      const signer = await provider.getSigner();
      const contract = new Contract(
        resolutionStorageAddress,
        resolutionStorageAbi,
        signer,
      );
      const tx = await contract.storeResolution(
        result.storage_payload.case_id,
        metadataHash,
        result.storage_payload.verdict,
        result.storage_payload.confidence_bps,
        result.storage_payload.metadata_uri,
      );
      setTxHash(tx.hash);
      setStatus("Transaction submitted to Sepolia.");
      await tx.wait();
      setStatus("Stored successfully on-chain.");
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Failed to store resolution.");
    } finally {
      setIsWriting(false);
    }
  }

  return (
    <article className="panel">
      <div className="panel-heading">
        <span className="panel-kicker">Wallet + Sepolia</span>
        <h2>Record the verdict on-chain</h2>
        <p>
          Connect a wallet, compute the deterministic resolution hash, then store it
          through the `ResolutionStorage` contract.
        </p>
      </div>

      <div className="wallet-state">
        {isConnected ? (
          <>
            <p>Connected wallet: {address}</p>
            <button type="button" className="button-secondary" onClick={handleDisconnect}>
              Disconnect
            </button>
          </>
        ) : (
          <button
            type="button"
            className="button-primary"
            onClick={handleConnect}
            disabled={isConnecting}
          >
            {isConnecting ? "Connecting..." : "Connect Wallet"}
          </button>
        )}
      </div>

      <div className="wallet-details">
        <p>
          Contract:{" "}
          {resolutionStorageAddress ?? "Set VITE_RESOLUTION_STORAGE_ADDRESS after deployment"}
        </p>
        <p>Resolution hash: {metadataHash ?? "Run a case first"}</p>
      </div>

      <button
        type="button"
        className="button-primary"
        onClick={handleStoreResolution}
        disabled={!isConnected || !result || !resolutionStorageAddress || isWriting}
      >
        {isWriting ? "Submitting to Sepolia..." : "Store Resolution"}
      </button>

      <p>{status}</p>
      {txHash ? <p>Transaction hash: {txHash}</p> : null}
    </article>
  );
}
