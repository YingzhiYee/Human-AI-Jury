// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

contract ResolutionStorage {
    struct ResolutionRecord {
        bytes32 caseKey;
        string caseId;
        bytes32 resolutionHash;
        string verdict;
        uint32 confidenceBps;
        string metadataURI;
        address resolver;
        uint64 createdAt;
    }

    mapping(bytes32 => ResolutionRecord) private records;

    event ResolutionStored(
        bytes32 indexed caseKey,
        string caseId,
        bytes32 indexed resolutionHash,
        string verdict,
        uint32 confidenceBps,
        address indexed resolver,
        string metadataURI
    );

    function storeResolution(
        string calldata caseId,
        bytes32 resolutionHash,
        string calldata verdict,
        uint32 confidenceBps,
        string calldata metadataURI
    ) external returns (bytes32 caseKey) {
        require(bytes(caseId).length > 0, "caseId required");
        require(bytes(verdict).length > 0, "verdict required");
        require(confidenceBps <= 10000, "confidence out of range");

        caseKey = keccak256(bytes(caseId));
        records[caseKey] = ResolutionRecord({
            caseKey: caseKey,
            caseId: caseId,
            resolutionHash: resolutionHash,
            verdict: verdict,
            confidenceBps: confidenceBps,
            metadataURI: metadataURI,
            resolver: msg.sender,
            createdAt: uint64(block.timestamp)
        });

        emit ResolutionStored(
            caseKey,
            caseId,
            resolutionHash,
            verdict,
            confidenceBps,
            msg.sender,
            metadataURI
        );
    }

    function getResolution(string calldata caseId)
        external
        view
        returns (ResolutionRecord memory)
    {
        return records[keccak256(bytes(caseId))];
    }
}
