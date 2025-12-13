document.addEventListener('DOMContentLoaded', function () {

    const btnLanjutPembayaran = document.getElementById("btn-lanjut-pembayaran");
    const modalKonfirmasi = document.getElementById("modal-konfirmasi");
    const selectKategori = document.getElementById("kategori_tempat_duduk");
    const form = document.getElementById("form-detail-pembeli");
    const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]')?.value;

    if (!btnLanjutPembayaran || !modalKonfirmasi || !form || !selectKategori) {
        console.error("Elemen penting tidak ditemukan");
        return;
    }

    btnLanjutPembayaran.addEventListener("click", async function () {
        try {
            const formData = new FormData(form);

            const matchId = document.getElementById("match_id")?.value;
            const kategoriId = selectKategori.value;

            if (!matchId || !kategoriId) {
                alert("Match atau kategori tidak valid");
                return;
            }

            // Kumpulkan tiket
            const tickets = [];
            let index = 1;
            while (formData.get(`nama_tiket_${index}`)) {
                tickets.push({
                    nama: formData.get(`nama_tiket_${index}`),
                    jenis_kelamin: formData.get(`jenis_kelamin_${index}`)
                });
                index++;
            }

            if (tickets.length === 0) {
                alert("Minimal 1 tiket harus diisi");
                return;
            }

            const payload = {
                match_id: parseInt(matchId),
                kategori_id: parseInt(kategoriId),
                nama_lengkap: formData.get("nama_lengkap"),
                email: formData.get("email"),
                nomor_telepon: formData.get("nomor_telepon"),
                tickets: tickets
            };

            console.log("Data dikirim:", payload);

            const response = await fetch("/payment/simpan_pembelian_ajax/", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "X-CSRFToken": csrfToken
                },
                body: JSON.stringify(payload)
            });

            if (!response.ok) {
                throw new Error(`Server error ${response.status}`);
            }

            const data = await response.json();

            if (data.status !== "success") {
                throw new Error(data.message || "Gagal menyimpan pembelian");
            }

            modalKonfirmasi.classList.add("hidden");
            window.location.href = `/payment/detail-pembayaran/${data.order_id}/`;

        } catch (err) {
            console.error(err);
            alert("Terjadi kesalahan saat berkomunikasi dengan server");
        }
    });

    // Tutup modal jika klik luar
    modalKonfirmasi.addEventListener("click", function (e) {
        if (e.target === modalKonfirmasi) {
            modalKonfirmasi.classList.add("hidden");
        }
    });
});
