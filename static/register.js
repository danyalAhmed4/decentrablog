const registerBtn = document.getElementById("registerBtn");
const registerResult = document.getElementById("registerResult");

function downloadPrivateKeyJson(content, did) {
    const blob = new Blob([content], { type: "application/json" });
    const fileUrl = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = fileUrl;
    a.download = `${did.replace(/[:]/g, "_")}_private_key.json`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(fileUrl);
}

registerBtn.addEventListener("click", async () => {
    registerResult.textContent = "Registering...";
    registerResult.className = "result";

    const name = document.getElementById("name").value.trim();
    const email = document.getElementById("email").value.trim();

    if (!name || !email) {
        registerResult.textContent = "Name and email are required.";
        registerResult.classList.add("error");
        return;
    }

    try {
        const response = await fetch("/register", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ name, email }),
        });

        const data = await response.json();
        if (!response.ok) {
            throw new Error(data.error || "Registration failed.");
        }

        registerResult.textContent =
            `DID: ${data.did}\n` +
            `Public Key: ${data.publicKey}\n` +
            `Transaction: ${data.txHash}`;
        registerResult.classList.add("success");

        downloadPrivateKeyJson(data.privateKeyDownload, data.did);
    } catch (error) {
        registerResult.textContent = error.message;
        registerResult.classList.add("error");
    }
});
