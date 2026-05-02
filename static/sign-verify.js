const verifyBtn = document.getElementById("verifyBtn");
const verifyResult = document.getElementById("verifyResult");
const DID_APP_ID = "did-web";

function normalizePrivateKey(value) {
    const trimmed = value.trim();
    if (!trimmed) return "";
    return trimmed.startsWith("0x") ? trimmed : `0x${trimmed}`;
}

verifyBtn.addEventListener("click", async () => {
    verifyResult.textContent = "Requesting challenge...";
    verifyResult.className = "result";

    const did = document.getElementById("did").value.trim();
    const privateKey = normalizePrivateKey(document.getElementById("privateKey").value);
    const appId = DID_APP_ID;

    if (!did || !privateKey) {
        verifyResult.textContent = "DID and private key are required.";
        verifyResult.classList.add("error");
        return;
    }

    try {
        const challengeRes = await fetch("/auth/request-challenge", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ did, appId }),
        });
        const challengeData = await challengeRes.json();
        if (!challengeRes.ok) {
            throw new Error(challengeData.error || "Challenge request failed.");
        }

        verifyResult.textContent = "Signing challenge message...";

        const wallet = new ethers.Wallet(privateKey);
        const signature = await wallet.signMessage(challengeData.message);

        verifyResult.textContent = "Verifying signature...";

        const verifyRes = await fetch("/auth/verify", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                did,
                message: challengeData.message,
                signature,
                nonce: challengeData.nonce,
                appId,
            }),
        });
        const verifyData = await verifyRes.json();

        if (!verifyRes.ok) {
            throw new Error(verifyData.error || "Verification failed.");
        }

        if (verifyData.verified) {
            verifyResult.textContent = `Verified ✅\nWelcome, ${verifyData.name}`;
            verifyResult.classList.add("success");
        } else {
            verifyResult.textContent = "Failed ❌";
            verifyResult.classList.add("error");
        }
    } catch (error) {
        verifyResult.textContent = `Failed ❌\n${error.message}`;
        verifyResult.classList.add("error");
    }
});
