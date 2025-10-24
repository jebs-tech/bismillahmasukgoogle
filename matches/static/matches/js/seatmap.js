async function loadSeats() {
  const res = await fetch(`/api/matches/${MATCH_ID}/seats/`);
  if (!res.ok) { console.error('fetch seats failed'); return; }
  const j = await res.json(); const seats = j.seats;
  const seatmap = document.getElementById('seatmap'); seatmap.innerHTML = '';

  const legend = document.getElementById('legend'); 
  const cats = {};
  seats.forEach(s => { if (!cats[s.category]) cats[s.category] = s; });
  legend.innerHTML = Object.keys(cats).map(k => `<span class="inline-flex items-center mr-4"><span style="width:12px;height:12px;border-radius:999px;background:${cats[k].color};display:inline-block;margin-right:6px;"></span>${k} Rp${cats[k].price}</span>`).join(' ');

  const rows = {};
  seats.forEach(s => { if (!rows[s.row]) rows[s.row] = []; rows[s.row].push(s); });
  const rowKeys = Object.keys(rows).sort();
  rowKeys.forEach(row => {
    const rowEl = document.createElement('div'); rowEl.className = 'flex items-center mb-2';
    const label = document.createElement('div'); label.className = 'w-10 font-medium'; label.innerText = row;
    rowEl.appendChild(label);
    rows[row].sort((a,b)=> a.col - b.col).forEach(s => {
      const btn = document.createElement('button');
      btn.className = 'seat inline-flex items-center justify-center w-9 h-9 mr-2 rounded-md border';
      btn.dataset.id = s.id; btn.dataset.price = s.price; btn.dataset.category = s.category;
      btn.innerText = s.col;
      btn.title = `${s.label} — ${s.category} — Rp${s.price}`;
      if (s.is_booked) { btn.classList.add('bg-gray-200','text-gray-500'); btn.disabled = true; }
      else { btn.style.borderColor = s.color; btn.addEventListener('click', toggleSeat); }
      rowEl.appendChild(btn);
    });
    seatmap.appendChild(rowEl);
  });
}

const selected = new Map();
function toggleSeat(e) {
  const btn = e.currentTarget; const id = btn.dataset.id;
  if (selected.has(id)) { selected.delete(id); btn.classList.remove('ring-4','ring-serve-accent'); btn.classList.remove('bg-amber-100'); }
  else { selected.set(id, {id, price: Number(btn.dataset.price), category: btn.dataset.category}); btn.classList.add('ring-4','ring-serve-accent'); btn.classList.add('bg-amber-100'); }
  renderSummary();
}

function renderSummary(){
  const list = document.getElementById('selected-list'); list.innerHTML = '';
  let total = 0;
  selected.forEach(s => { const el = document.createElement('div'); el.className='text-sm'; el.innerText = `${s.category} - Rp${s.price}`; list.appendChild(el); total += s.price; });
  document.getElementById('total-price').innerText = `Rp${total}`;
}

async function postBooking(payload){
  const res = await fetch('/api/book/', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(payload) });
  return res.json();
}

window.addEventListener('DOMContentLoaded', () => {
  loadSeats();

  const bookBtn = document.getElementById('book-btn');
  if (bookBtn) {
    bookBtn.addEventListener('click', async () => {
      const buyer_name = document.getElementById('buyer_name').value;
      const buyer_email = document.getElementById('buyer_email').value;
      if (!buyer_name || !buyer_email) { alert('Isi nama dan email'); return; }
      if (selected.size === 0) { alert('Pilih kursi terlebih dahulu'); return; }
      const payload = { match_id: MATCH_ID, seat_ids: Array.from(selected.keys()).map(x=>Number(x)), buyer_name, buyer_email };
      const out = document.getElementById('book-result'); out.innerText = 'Memproses...';
      try {
        const j = await postBooking(payload);
        if (j.ok) { out.innerText = `Pesanan sukses. Booking ID: ${j.booking_id}. Total Rp${j.total_price}`; selected.clear(); renderSummary(); await loadSeats(); }
        else out.innerText = `Gagal: ${j.msg || JSON.stringify(j)}`;
      } catch(err) { out.innerText = 'Terjadi kesalahan.'; console.error(err); }
    });
  }

  const bookTicketsBtn = document.getElementById('book-tickets');
  if (bookTicketsBtn) {
    bookTicketsBtn.addEventListener('click', ()=> {
      const buyer = document.getElementById('buyer_name');
      if (buyer) buyer.scrollIntoView({behavior:'smooth', block:'center'});
    });
  }
});
