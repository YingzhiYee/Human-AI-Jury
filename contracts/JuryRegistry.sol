// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

contract JuryRegistry {
    struct JurorProfile {
        bool active;
        string handle;
        string metadataURI;
        uint64 joinedAt;
    }

    mapping(address => JurorProfile) public jurors;

    event JurorRegistered(address indexed juror, string handle, string metadataURI);
    event JurorStatusUpdated(address indexed juror, bool active);

    function register(string calldata handle, string calldata metadataURI) external {
        require(bytes(handle).length > 0, "handle required");
        jurors[msg.sender] = JurorProfile({
            active: true,
            handle: handle,
            metadataURI: metadataURI,
            joinedAt: uint64(block.timestamp)
        });
        emit JurorRegistered(msg.sender, handle, metadataURI);
    }

    function setActive(bool active) external {
        require(bytes(jurors[msg.sender].handle).length > 0, "juror not registered");
        jurors[msg.sender].active = active;
        emit JurorStatusUpdated(msg.sender, active);
    }
}
