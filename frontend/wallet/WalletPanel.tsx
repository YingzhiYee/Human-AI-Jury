import { useState } from "react";
import { BrowserProvider, Contract, keccak256, toUtf8Bytes } from "ethers";

import { resolutionStorageAbi } from "../lib/contracts";
import { useSession } from "../lib/session";

const SEPOLIA_CHAIN_ID = "0xaa36a7";
const DEFAULT_RESOLUTION_STORAGE_ADDRESS =
  "0x76Bcbb0b0E44fdd6626dd709C59d396d03eFF086";
const resolutionStorageAddress =
  (import.meta.env.VITE_RESOLUTION_STORAGE_ADDRESS as string | undefined) ??
  DEFAULT_RESOLUTION_STORAGE_ADDRESS;
const contractExplorerUrl = `https://sepolia.etherscan.io/address/${resolutionStorageAddress}`;

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

  async function ensureSepolia() {
    if (!window.ethereum) {
      throw new Error("No injected wallet found.");
    }

    const chainId = (await window.ethereum.request({
      method: "eth_chainId",
    })) as string;

    if (chainId !== SEPOLIA_CHAIN_ID) {
      await window.ethereum.request({
        method: "wallet_switchEthereumChain",
        params: [{ chainId: SEPOLIA_CHAIN_ID }],
      });
    }
  }

  async function handleConnect() {
    if (!window.ethereum) {
      setStatus("No injected wallet found. Install MetaMask or another EIP-1193 wallet.");
      return;
    }

    setIsConnecting(true);
    try {
      await ensureSepolia();
      const accounts = (await window.ethereum.request({
        method: "eth_requestAccounts",
      })) as string[];
      setAddress(accounts[0] ?? null);
      setStatus("Wallet connected on Sepolia.");
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
    if (!result || !metadataHash) {
      setStatus("Missing result, contract address, or metadata hash.");
      return;
    }

    if (!window.ethereum) {
      setStatus("No injected wallet found for contract write.");
      return;
    }

    setIsWriting(true);
    try {
      await ensureSepolia();
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
          Contract: <a href={contractExplorerUrl} target="_blank" rel="noreferrer">{resolutionStorageAddress}</a>
        </p>
        <p>Resolution hash: {metadataHash ?? "Run a case first"}</p>
      </div>

      <button
        type="button"
        className="button-primary"
        onClick={handleStoreResolution}
        disabled={!isConnected || !result || isWriting}
      >
        {isWriting ? "Submitting to Sepolia..." : "Store Resolution"}
      </button>

      <p>{status}</p>
      {txHash ? (
        <p>
          Transaction hash:{" "}
          <a
            href={`https://sepolia.etherscan.io/tx/${txHash}`}
            target="_blank"
            rel="noreferrer"
          >
            {txHash}
          </a>
        </p>
      ) : null}
    </article>
  );
}
