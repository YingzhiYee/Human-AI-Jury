export const resolutionStorageAbi = [
  {
    type: "function",
    name: "storeResolution",
    stateMutability: "nonpayable",
    inputs: [
      { name: "caseId", type: "string" },
      { name: "resolutionHash", type: "bytes32" },
      { name: "verdict", type: "string" },
      { name: "confidenceBps", type: "uint32" },
      { name: "metadataURI", type: "string" },
    ],
    outputs: [{ name: "caseKey", type: "bytes32" }],
  },
] as const;
