export default function({parentElement, data}) {
  const root = parentElement.querySelector('.classification-details');
  root.dashboardCleanup?.();
  if (root.dashboardContext !== data.context) {
    root.dashboardContext = data.context;
    root.dashboardExpanded = false;
    root.replaceChildren();
    const head = document.createElement('div');
    head.className = 'classification-heading';
    const title = document.createElement('h3');
    title.textContent = `${data.category} 세부 명칭`;
    const count = document.createElement('span');
    count.className = 'classification-count';
    count.textContent = `${data.names.length.toLocaleString()}개`;
    head.append(title, count);
    const tags = document.createElement('div');
    tags.className = 'classification-tags';
    tags.id = `classification-tags-${crypto.randomUUID()}`;
    for (const name of data.names) {
      const tag = document.createElement('span');
      tag.className = 'classification-name';
      tag.textContent = name;
      tags.append(tag);
    }
    const empty = document.createElement('p');
    empty.className = 'classification-empty';
    empty.textContent = '등록된 세부 명칭이 없습니다.';
    empty.hidden = data.names.length > 0;
    const toggle = document.createElement('button');
    toggle.className = 'classification-toggle';
    toggle.type = 'button';
    toggle.setAttribute('aria-controls', tags.id);
    root.append(head, tags, empty, toggle);
  }
  const tags = root.querySelector('.classification-tags');
  const toggle = root.querySelector('.classification-toggle');
  let disposed = false, scheduled;
  const fit = () => {
    if (disposed) return;
    tags.style.maxHeight = 'none';
    const nodes = [...tags.children];
    const positions = nodes.map(node => node.getBoundingClientRect().top);
    const rows = [...new Set(positions.map(top => Math.round(top)))];
    const overflows = rows.length > 2;
    const third = rows[2];
    const shown = overflows ? positions.filter(top => Math.round(top) < third).length : nodes.length;
    if (!root.dashboardExpanded && overflows) {
      tags.style.maxHeight = `${third - tags.getBoundingClientRect().top - 8}px`;
    }
    nodes.forEach((node, index) => node.setAttribute('aria-hidden', String(!root.dashboardExpanded && index >= shown)));
    toggle.hidden = !overflows;
    toggle.textContent = root.dashboardExpanded ? '접기 ⌃' : `더보기 (${(nodes.length - shown).toLocaleString()}개) ⌄`;
    toggle.setAttribute('aria-expanded', String(Boolean(root.dashboardExpanded)));
  };
  const schedule = () => {
    cancelAnimationFrame(scheduled);
    scheduled = requestAnimationFrame(fit);
  };
  const expand = () => {
    root.dashboardExpanded = !root.dashboardExpanded;
    fit();
  };
  toggle.addEventListener('click', expand);
  let width;
  const observer = new ResizeObserver(entries => {
    const current = entries[0].contentRect.width;
    if (current !== width) { width = current; schedule(); }
  });
  observer.observe(root);
  document.fonts.ready.then(schedule);
  schedule();
  const cleanup = () => {
    disposed = true;
    cancelAnimationFrame(scheduled);
    observer.disconnect();
    toggle.removeEventListener('click', expand);
  };
  root.dashboardCleanup = cleanup;
  return cleanup;
}
