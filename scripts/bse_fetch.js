// Runs in a browser tab on https://www.bseindia.com/ (steps in bse_fetch.py). Defines window.__bseRun(job), which
// calls BSE's API as the site itself does, keeps the answers in window.__bse.out and returns at once. Paste this file
// once per tab; later batches only call __bseRun with the job that `bse_fetch.py job` prints.
window.__bseRun = job => {
  const st = window.__bse = {job, out: {}, done: 0, errors: [], finished: false}, A = 'https://api.bseindia.com/BseIndiaAPI/api/';
  const get = async url => { await new Promise(r => setTimeout(r, 800)); const r = await fetch(url); if (!r.ok) throw new Error(r.status + ' ' + url); return r.json(); };
  (async () => {
    const codes = {};
    if (job.syms.some(s => !/^\d+$/.test(s))) {
      for (const x of await get(A + 'ListofScripData/w?Group=&Scripcode=&industry=&segment=Equity&status=Active')) codes[(x.scrip_id || '').toUpperCase()] = x.SCRIP_CD;
    }
    for (const sym of job.syms) {
      const c = /^\d+$/.test(sym) ? sym : codes[sym.toUpperCase()], o = st.out[sym] = {code: c};
      if (!c) { st.errors.push(sym + ': not on BSE list'); st.done++; continue; }
      const urls = {pledge: 'ConsolidatePledge/w?scripcode=' + c, shp: 'TabResults_SHP/w?scripcode=' + c,
                    results: 'Integratedfinancedata/w?scripcode=' + c, actions: 'CorporateAction/w?scripcode=' + c};
      for (const item of job.items) {
        try {
          if (item === 'announcements') {
            const rows = [], seen = new Set();  // no page count in the answer: page until a page adds nothing new
            for (let p = 1; p <= 40; p++) {
              const t = ((await get(A + `AnnSubCategoryGetData/w?pageno=${p}&strCat=-1&strPrevDate=${job.from}&strScrip=${c}&strSearch=P&strToDate=${job.to}&strType=C&subcategory=-1`)).Table || [])
                .filter(x => !seen.has(x.NEWSID) && seen.add(x.NEWSID));
              if (!t.length) break;
              rows.push(...t);
            }
            o[item] = {url: A + `AnnSubCategoryGetData/w?strScrip=${c}&strPrevDate=${job.from}&strToDate=${job.to}`, data: rows};
          } else {
            o[item] = {url: A + urls[item], data: await get(A + urls[item])};
          }
        } catch (e) { st.errors.push(sym + ' ' + item + ': ' + e.message); o[item] = {url: A + (urls[item] || item), error: String(e.message)}; }
      }
      st.done++;
    }
    st.finished = true;
  })().catch(e => { st.errors.push(String(e)); st.finished = true; });
  return 'started ' + job.syms.length;
};
'defined'
