'use strict';

const $ = id => document.getElementById(id);
const metricNames = ['犯罪率', '公寓占比', '停车难度', '商务地址密度'];
const weights = [.2, .3, .25, .25];
const selected = new Set(), byZip = new Map(), layers = new Map();
let activeRegion = 'all', focused = null, displayLayer = 'total', geoLayer, features = [], meta = null;

const layerLabels = {
  total: '综合难度 · 公开数据模型',
  apartment: '公寓占比 · ACS 2020–2024',
  crime: '犯罪构成分 · 分地区同口径排名',
  parking: '停车难度 · OSM 静态道路代理',
  business: '商业机构密度 · ZBP 2023'
};
const map = L.map('map', {zoomControl: false, minZoom: 6, maxZoom: 16, zoomSnap: .25, preferCanvas: false}).setView([40.6, -74], 9);
L.control.zoom({position: 'bottomright'}).addTo(map);
const tiles = L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
  maxZoom: 19,
  attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
}).addTo(map);
let tileFailed = false;
tiles.on('tileerror', () => {
  if (!tileFailed) {
    tileFailed = true;
    $('status').textContent = '背景底图暂时不可用；邮编边界和选择功能仍可使用。';
  }
});

function metrics(zip) { return byZip.get(zip)?.properties.scores ?? [null, null, null, null]; }
function score(zip) {
  const values = metrics(zip);
  return values.some(value => value === null) ? null : values.reduce((sum, value, index) => sum + value * weights[index], 0);
}
function avg(values) { return values.length ? values.reduce((a, b) => a + b, 0) / values.length : null; }
function fmt(value) { return value === null || value === undefined ? '—' : Number(value).toFixed(1); }
function escapeText(value) { return String(value).replace(/[&<>"']/g, char => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'}[char])); }
function color(value) { return value === null ? '#f4f6f8' : value < 20 ? '#38a997' : value < 40 ? '#9dc992' : value < 60 ? '#e9cf62' : value < 80 ? '#e39c55' : '#c75a4d'; }
function layerValue(zip) {
  const index = {crime: 0, apartment: 1, parking: 2, business: 3}[displayLayer];
  return displayLayer === 'total' ? score(zip) : metrics(zip)[index];
}
function matches(feature) {
  const props = feature.properties;
  return activeRegion === 'all' || (activeRegion === 'brooklyn' ? props.area === '布鲁克林' : props.region === activeRegion);
}
function style(feature) {
  const zip = feature.properties.zip;
  return {
    fillColor: color(layerValue(zip)), fillOpacity: selected.has(zip) ? .86 : .55,
    color: selected.has(zip) ? '#112d47' : '#73877d', weight: selected.has(zip) ? 2.7 : .65,
    opacity: selected.has(zip) ? 1 : .6, dashArray: layerValue(zip) === null ? '3 3' : null
  };
}

function crimeSourceKey(props) {
  if (props.crime_source?.kind === 'nyc_zcta') return 'crime_nyc';
  if (props.crime_source?.kind === 'li_county') return 'crime_li';
  return 'crime_nj';
}
function sourceKey(props, index) {
  return index === 0 ? crimeSourceKey(props) : index === 1 ? 'housing' : index === 2 ? 'parking' : 'business';
}
function rawMetric(props, index) {
  if (index === 0) {
    if (props.crime_score === null || props.crime_score === undefined) return '缺少可用犯罪分项';
    return `${props.crime_source.label} · ${props.crime_source.geography}`;
  }
  if (index === 1) {
    return props.apartment_pct === null ? '未发布可用住房估计值' : `${fmt(props.apartment_pct)}% · ${props.apartment_units.toLocaleString()} / ${props.housing_total.toLocaleString()} 住房单元`;
  }
  if (index === 2) {
    return props.parking_score === null ? '缺少公开路网数据' : `公开道路结构综合代理 · ${fmt(props.parking_score)} 分`;
  }
  return props.business_density === null ? '未匹配到商业机构数据' : `${fmt(props.business_density)} 家 / km² · ${props.business_establishments.toLocaleString()} 家机构`;
}
function tooltip(zip) {
  const props = byZip.get(zip).properties;
  let value;
  if (displayLayer === 'total') {
    value = score(zip) === null ? `综合分缺失 · 已接入 ${metrics(zip).filter(item => item !== null).length}/4 项` : `综合预估 ${fmt(score(zip))} / 100`;
  } else {
    value = rawMetric(props, {crime: 0, apartment: 1, parking: 2, business: 3}[displayLayer]);
  }
  return `<b>${zip}</b> · ${escapeText(props.area)}<br>${escapeText(value)}<br><small>${selected.has(zip) ? '点击取消选择' : '点击加入线路'}</small>`;
}
function updateLayers() {
  for (const [zip, layer] of layers) {
    layer.setStyle(style(byZip.get(zip)));
    layer.setTooltipContent(tooltip(zip));
    const element = layer.getElement();
    if (element) element.setAttribute('aria-pressed', String(selected.has(zip)));
    if (selected.has(zip)) layer.bringToFront();
  }
}
function fitRegion() {
  if (geoLayer && geoLayer.getLayers().length) map.fitBounds(geoLayer.getBounds(), {padding: [38, 45], maxZoom: 11, animate: false});
}
function drawRegion(fit = true) {
  if (geoLayer) map.removeLayer(geoLayer);
  layers.clear();
  const visible = features.filter(matches);
  geoLayer = L.geoJSON(visible, {
    style,
    onEachFeature: (feature, layer) => {
      const zip = feature.properties.zip;
      layers.set(zip, layer);
      layer.bindTooltip(tooltip(zip), {sticky: true});
      layer.on('click', () => toggleZip(zip));
      layer.on('mouseover', () => layer.setStyle({weight: 2, color: '#263f55', fillOpacity: .8}));
      layer.on('mouseout', () => layer.setStyle(style(feature)));
    }
  }).addTo(map);
  for (const [zip, layer] of layers) {
    const element = layer.getElement();
    if (!element) continue;
    element.setAttribute('role', 'button');
    element.setAttribute('tabindex', '0');
    element.setAttribute('aria-label', `邮编 ${zip} · ${byZip.get(zip).properties.area}`);
    element.setAttribute('aria-pressed', String(selected.has(zip)));
    element.addEventListener('keydown', event => {
      if (event.key === 'Enter' || event.key === ' ') {
        event.preventDefault();
        toggleZip(zip);
      }
    });
  }
  $('coverage').textContent = `${visible.length} 个邮编区域`;
  if (fit) fitRegion();
}
function toggleZip(zip) {
  if (!byZip.has(zip)) throw new Error('该邮编不在当前范围中');
  if (selected.has(zip)) {
    selected.delete(zip);
    if (focused === zip) focused = null;
  } else {
    selected.add(zip);
    focused = zip;
  }
  render();
  updateLayers();
}
function setRegion(region, fit = true) {
  activeRegion = region;
  document.querySelectorAll('[data-region]').forEach(button => button.classList.toggle('active', button.dataset.region === region));
  drawRegion(fit);
}
function focusZip(zip) {
  focused = zip;
  const feature = byZip.get(zip);
  if (!matches(feature)) setRegion('all', false);
  const layer = layers.get(zip);
  if (layer) map.fitBounds(layer.getBounds(), {padding: [65, 65], maxZoom: 13, animate: false});
  render();
}

function componentMarkup(props, index) {
  const components = index === 0 ? props.crime_components : index === 2 ? props.parking_components : null;
  if (!components?.length) return '';
  const items = components.map(item => {
    const detail = item.detail || `${fmt(item.rate_per_100000)} 件 / 10万人${item.count === undefined ? '' : ` · ${item.count.toLocaleString()} 件`}`;
    return `<div class="submetric"><div><span>${escapeText(item.label)} <em>${Math.round(item.weight * 100)}%</em></span><b>${fmt(item.score)}</b></div><small>${escapeText(detail)}</small></div>`;
  }).join('');
  let evidence = '';
  if (index === 2 && props.parking_points !== undefined) {
    evidence = `<div class="evidence">NYC补充证据：全天禁停/禁候标志 ${props.parking_points.toLocaleString()} 个 · ${fmt(props.parking_density)} 个/km²（不计分）</div>`;
  }
  return `<div class="submetrics">${items}${evidence}</div>`;
}

function render() {
  const zipCodes = [...selected], totals = zipCodes.map(score);
  const complete = totals.length > 0 && totals.every(value => value !== null);
  const average = complete ? avg(totals) : null;
  const completeCount = totals.filter(value => value !== null).length;
  $('average').textContent = fmt(average);
  $('count').textContent = zipCodes.length;
  $('selectedCount').textContent = zipCodes.length;
  $('min').textContent = complete ? fmt(Math.min(...totals)) : '—';
  $('max').textContent = complete ? fmt(Math.max(...totals)) : '—';
  $('level').textContent = !zipCodes.length ? '待选择' : average === null ? '数据不足' : average < 40 ? '较容易' : average < 60 ? '中等' : average < 80 ? '较困难' : '困难';
  $('clear').disabled = !zipCodes.length;
  $('scoreType').textContent = '公开数据模型';
  $('dataStatus').textContent = !zipCodes.length ? '犯罪和停车已拆成公开分项；点击邮编可查看原始率、代理值和来源。' : complete ? `全部 ${zipCodes.length} 个邮编四项齐全，按邮编等权平均。` : `仅 ${completeCount} / ${zipCodes.length} 个邮编四项齐全；缺失值不按零分。`;

  const container = $('selection');
  container.replaceChildren();
  if (!zipCodes.length) container.innerHTML = '<div class="empty"><span>＋</span><b>从地图开始选择</b><p>点击邮编查看公开指标，<br>多选自动汇总；缺失不按零分。</p></div>';
  for (const zip of zipCodes) {
    const row = document.createElement('div');
    row.className = `zip-row${focused === zip ? ' focused' : ''}`;
    const button = document.createElement('button');
    button.className = 'zip-focus';
    button.innerHTML = `<b>${zip}</b><small>${escapeText(byZip.get(zip).properties.area)}</small>`;
    button.setAttribute('aria-label', `查看邮编 ${zip} 的指标`);
    button.onclick = () => focusZip(zip);
    const value = document.createElement('span');
    value.className = 'zip-score';
    value.textContent = score(zip) === null ? `${metrics(zip).filter(item => item !== null).length}/4 项` : fmt(score(zip));
    const remove = document.createElement('button');
    remove.className = 'remove';
    remove.textContent = '×';
    remove.setAttribute('aria-label', `取消邮编 ${zip}`);
    remove.onclick = () => toggleZip(zip);
    row.append(button, value, remove);
    container.append(row);
  }

  const single = focused && selected.has(focused), detailZips = single ? [focused] : zipCodes;
  const metricAverages = metricNames.map((_, index) => {
    const values = detailZips.map(zip => metrics(zip)[index]);
    return values.length && values.every(value => value !== null) ? avg(values) : null;
  });
  $('detailTitle').textContent = single ? `${focused} · 指标明细` : '指标明细';
  $('detailSub').textContent = single ? '单个邮编' : '所选邮编平均';
  $('metrics').innerHTML = metricNames.map((name, index) => {
    const known = detailZips.filter(zip => metrics(zip)[index] !== null).length;
    const props = single ? byZip.get(focused).properties : null;
    const raw = single ? rawMetric(props, index) : detailZips.length ? (known === detailZips.length ? `邮编等权平均 · 加权贡献 ${fmt(metricAverages[index] * weights[index])} 分` : `${known}/${detailZips.length} 个邮编有此项数据`) : '选择邮编后显示原始数据';
    const key = props ? sourceKey(props, index) : index === 1 ? 'housing' : index === 2 ? 'parking' : index === 3 ? 'business' : 'crime_nyc';
    const source = meta?.sources[key];
    const label = index === 0 ? '公开犯罪分项 · 地区内百分位' : index === 1 ? 'ACS · 2户及以上建筑' : index === 2 ? 'OSM路网 · 静态停车代理' : 'ZBP · 商业机构密度代理';
    return `<div class="metric"><div class="metric-top"><span>${name}<em>${Math.round(weights[index] * 100)}%</em></span><b>${fmt(metricAverages[index])}${metricAverages[index] !== null ? ' 分' : ''}</b></div><div class="metric-track"><div style="width:${metricAverages[index] ?? 0}%"></div></div><div class="metric-raw">${escapeText(raw)}</div>${single ? componentMarkup(props, index) : ''}<div class="metric-foot">${label}${source ? ` · <a href="${source.url}" target="_blank" rel="noopener">来源 ↗</a>` : ''}</div></div>`;
  }).join('');
}

$('searchForm').onsubmit = event => {
  event.preventDefault();
  const zip = $('zipSearch').value.trim();
  if (!byZip.has(zip)) {
    $('status').textContent = `邮编 ${zip} 不在当前范围内：曼哈顿和新泽西南界以南已排除；部分特殊邮编没有ZCTA边界。`;
    return;
  }
  $('status').textContent = `已定位 ${zip}；重复搜索不会重复计数。`;
  selected.add(zip);
  focusZip(zip);
  updateLayers();
};
$('clear').onclick = () => { selected.clear(); focused = null; render(); updateLayers(); $('status').textContent = '已清空选择。'; };
$('resetView').onclick = fitRegion;
document.querySelectorAll('[data-region]').forEach(button => button.onclick = () => setRegion(button.dataset.region));
$('mode').onchange = event => {
  displayLayer = event.target.value;
  $('legendTitle').textContent = layerLabels[displayLayer];
  $('legendFoot').textContent = displayLayer === 'apartment' ? '按真实占比着色 · 浅色虚线 = 缺失' : '0–100 分 · 浅色虚线 = 缺失';
  $('legendTicks').innerHTML = displayLayer === 'apartment' ? '<span>0%</span><span>50%</span><span>100%</span>' : '<span>0 低</span><span>50</span><span>100 高</span>';
  updateLayers();
};
$('methodBtn').onclick = () => $('method').showModal();
$('closeMethod').onclick = () => $('method').close();
$('method').onclick = event => {
  if (event.target !== $('method')) return;
  const bounds = $('method').getBoundingClientRect();
  if (event.clientX < bounds.left || event.clientX > bounds.right || event.clientY < bounds.top || event.clientY > bounds.bottom) $('method').close();
};

function stateResult() {
  const zipCodes = [...selected], totals = zipCodes.map(score);
  return {
    dataMode: 'public_data_model', mapLayer: displayLayer, selected: zipCodes,
    average: totals.length && totals.every(value => value !== null) ? avg(totals) : null,
    completeZips: totals.filter(value => value !== null).length,
    scoreStatus: totals.length && totals.every(value => value !== null) ? 'model_estimate' : 'incomplete',
    metrics: zipCodes.map(zip => ({zip, scores: metrics(zip)}))
  };
}
function selectBatch(input) {
  if (!input || !Array.isArray(input.zipCodes) || !input.zipCodes.every(zip => typeof zip === 'string' && /^\d{5}$/.test(zip) && byZip.has(zip))) throw new Error('请提供地图当前范围内的5位邮编数组');
  selected.clear();
  input.zipCodes.forEach(zip => selected.add(zip));
  focused = null;
  render();
  updateLayers();
  return stateResult();
}
function registerTools() {
  const context = document.modelContext;
  if (!context?.registerTool) return;
  const tools = [
    {name: 'select_zip_codes', description: '替换地图所选邮编，并返回公开数据模型计算的线路难度。', inputSchema: {type: 'object', properties: {zipCodes: {type: 'array', items: {type: 'string', pattern: '^\\d{5}$'}}}, required: ['zipCodes'], additionalProperties: false}, annotations: {readOnlyHint: false}, execute: selectBatch},
    {name: 'get_route_selection', description: '读取所选邮编及公开数据模型计算的基础难度。', inputSchema: {type: 'object', properties: {}, additionalProperties: false}, annotations: {readOnlyHint: true}, execute: stateResult}
  ];
  for (const tool of tools) {
    try { Promise.resolve(context.registerTool(tool)).catch(() => {}); } catch {}
  }
}
function showMetadata() {
  const counts = meta.counts;
  $('notice').innerHTML = `<span>公开数据</span>犯罪 ${counts.crime}/${counts.total} · 停车代理 ${counts.parking}/${counts.total} · 公寓 ${counts.housing}/${counts.total} · 商务 ${counts.business}/${counts.total} · 综合可计算 ${counts.complete}/${counts.total}。`;
  const keys = ['crime_nyc', 'crime_li', 'crime_nj', 'parking', 'parking_nyc', 'housing', 'business'];
  $('sourceDetails').innerHTML = keys.map(key => `<p><a href="${meta.sources[key].url}" target="_blank" rel="noopener">${meta.sources[key].title} ↗</a><br>${meta.sources[key].method}</p>`).join('') + `<p>数据下载于 ${meta.retrieved}。NYC进入模型的7类重罪 ${meta.crime_audit.model_group_records.toLocaleString()} 件，其中 ${meta.crime_audit.mapped_model_group_records.toLocaleString()} 件可归属本地图ZCTA。NJ ${meta.counts.crime_nj_agency} 个邮编映射到执法机构，${meta.counts.crime_nj_fallback} 个采用县级机构汇总。</p>`;
  const points = meta.boundary_anchors.map(anchor => [anchor.lat, anchor.lon]);
  L.polyline([[points[0][0], -75.6], ...points, [points.at(-1)[0], -73.95]], {color: '#324558', weight: 2, dashArray: '7 6', opacity: .9, interactive: false}).addTo(map);
  for (const anchor of meta.boundary_anchors) L.circleMarker([anchor.lat, anchor.lon], {radius: 4, color: '#142c40', fillColor: '#fff', fillOpacity: 1, weight: 2}).bindTooltip(`${anchor.zip} · 保留的南界参考邮编`).addTo(map);
}

render();
Promise.all([
  Promise.resolve(JSON.parse($('zip-data').textContent)),
  Promise.resolve(JSON.parse($('data-meta').textContent))
]).then(([json, metadata]) => {
  meta = metadata;
  features = json.features;
  for (const feature of features) byZip.set(feature.properties.zip, feature);
  drawRegion();
  new ResizeObserver(() => map.invalidateSize()).observe($('map'));
  showMetadata();
  $('mode').onchange({target: {value: displayLayer}});
  render();
  $('mapLoading').hidden = true;
  registerTools();
}).catch(() => {
  $('mapLoading').textContent = '公开数据载入失败，请刷新页面重试。';
  $('coverage').textContent = '数据不可用';
});
