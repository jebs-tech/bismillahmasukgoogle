document.getElementById("btn-lanjut-pembayaran").addEventListener("click", async function () {
    try {
        const response = await fetch("/payment/simpan_pembelian_ajax/", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify({
                match_id: MATCH_ID_DARI_TEMPLATE,
                kategori_id: KATEGORI_ID_DARI_SELECT,
                nama_lengkap: document.getElementById("nama").value,
                email: document.getElementById("email").value,
                nomor_telepon: document.getElementById("telepon").value,
                tickets: [{ dummy: true }] // minimal 1
            })
        });

        const data = await response.json();

        if (!response.ok) {
            alert(data.message || "Terjadi kesalahan");
            return;
        }

        window.location.href = `/payment/detail-pembayaran/${data.order_id}/`;

    } catch (err) {
        alert("Gagal komunikasi dengan server");
        console.error(err);
    }
});
