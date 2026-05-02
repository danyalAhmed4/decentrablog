// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract DIDRegistry {
    struct Identity {
        string did;
        string name;
        string email;
        address publicKey;
    }

    mapping(string => Identity) public identities;
    mapping(bytes32 => bool) private registeredIdentityKeys;

    event IdentityRegistered(string did, address publicKey);

    function registerIdentity(
        string memory did,
        string memory name,
        string memory email,
        address publicKey
    ) public {
        require(bytes(did).length != 0, "DID is required");
        require(bytes(name).length != 0, "Name is required");
        require(bytes(email).length != 0, "Email is required");
        require(publicKey != address(0), "Invalid public key");
        require(bytes(identities[did].did).length == 0, "DID already exists");

        bytes32 identityKey = _identityKey(name, email);
        require(!registeredIdentityKeys[identityKey], "Name and email already registered");

        identities[did] = Identity({
            did: did,
            name: name,
            email: email,
            publicKey: publicKey
        });
        registeredIdentityKeys[identityKey] = true;

        emit IdentityRegistered(did, publicKey);
    }

    function getIdentity(
        string memory did
    ) public view returns (string memory name, string memory email, address publicKey) {
        Identity storage identity = identities[did];
        return (identity.name, identity.email, identity.publicKey);
    }

    function verifyDIDExists(string memory did) public view returns (bool) {
        return bytes(identities[did].did).length != 0;
    }

    function verifyIdentityExistsByNameEmail(
        string memory name,
        string memory email
    ) public view returns (bool) {
        return registeredIdentityKeys[_identityKey(name, email)];
    }

    function _identityKey(string memory name, string memory email) private pure returns (bytes32) {
        return keccak256(abi.encodePacked(name, "|", email));
    }
}
