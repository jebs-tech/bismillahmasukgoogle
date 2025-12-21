(async function(){
  window.loadMatchesByMonth = async function(month, year, targetSelector='#matches-result'){
    const el = document.querySelector(targetSelector);
    if(!el) return;
    const url = `/servetix/api/matches/search/?month=${encodeURIComponent(month)}&year=${encodeURIComponent(year)}`;
    try {
      const resp = await fetch(url, {credentials:'same-origin'});
      if(!resp.ok) { el.innerHTML = '<p>Error</p>'; return; }
      const data = await resp.json();
      if(!data.matches || data.matches.length === 0){ el.innerHTML = '<p>No matches.</p>'; return; }
      let html = '<ul>';
      data.matches.forEach(m => {
        html += `<li><strong>${m.home_team}</strong> vs <strong>${m.away_team}</strong> — ${m.start_time_fmt} @ ${m.venue || 'No venue'}</li>`;
      });
      html += '</ul>';
      el.innerHTML = html;
    } catch(e){
      el.innerHTML = '<p>Error</p>';
      console.error(e);
    }
  };
})();
