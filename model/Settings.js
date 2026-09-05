// Pure, shared configuration/payload contract. Also exercised under Node.
var instruments = ['connection', 'processes', 'machine', 'storage', 'audio'];
var defaults = {
    version: 1, defaultInstrument: 'connection', lastInstrument: 'connection',
    animation: 'normal', refreshProfile: 'balanced', loopback: true, listeners: true,
    naming: 'local', labels: 'balanced', privacy: false, barMode: 'icon',
    introSeen: false, audioActions: false, aliases: {}, offlineDb: ''
};
var keys = {version:'tdVersion', defaultInstrument:'tdDefaultInstrument', lastInstrument:'tdLastInstrument',
    animation:'tdAnimation', refreshProfile:'tdRefreshProfile', loopback:'tdLoopback', listeners:'tdListeners',
    naming:'tdNaming', labels:'tdLabels', privacy:'tdPrivacy', barMode:'tdBarMode', introSeen:'tdIntroSeen',
    audioActions:'tdAudioActions', aliases:'tdAliases', offlineDb:'tdOfflineDb'};
function object(v) { return v !== null && typeof v === 'object' && !Array.isArray(v); }
function safeText(v,n) { return typeof v === 'string' ? v.replace(/[\x00-\x1f\x7f-\x9f\u202a-\u202e\u2066-\u2069]/g,'').slice(0,n || 512) : ''; }
function copy(v) { return JSON.parse(JSON.stringify(v)); }
function normalize(entry) {
    entry = object(entry) ? entry : {};
    var out = copy(defaults), warnings = [];
    Object.keys(keys).forEach(function(k) {
        if (entry[keys[k]] !== undefined) out[k] = entry[keys[k]];
    });
    var choices = {defaultInstrument:instruments,lastInstrument:instruments,animation:['reduced','normal','vivid'],
        refreshProfile:['efficient','balanced','responsive'],naming:['raw','local','dns'],labels:['minimal','balanced','dense'],barMode:['icon','label']};
    Object.keys(choices).forEach(function(k) {
        if (choices[k].indexOf(out[k]) < 0) { out[k] = defaults[k]; warnings.push(k + ': repaired invalid value'); }
    });
    ['loopback','listeners','privacy','introSeen','audioActions'].forEach(function(k) {
        if (typeof out[k] !== 'boolean') { out[k] = defaults[k]; warnings.push(k + ': expected boolean'); }
    });
    var aliases = {};
    if (object(out.aliases)) Object.keys(out.aliases).slice(0,512).forEach(function(k) {
        // Backend validates actual IP syntax; renderer never executes aliases.
        if (/^[0-9a-fA-F:.]+$/.test(k) && typeof out.aliases[k] === 'string') aliases[k] = safeText(out.aliases[k],253);
    });
    out.aliases = aliases;
    out.offlineDb = safeText(out.offlineDb,4096);
    var newer = Number(out.version) > 1;
    if (newer) warnings.push('Settings belong to a newer version; changes are read-only until migrated.');
    out.version = 1;
    return {values:out, warnings:warnings, readOnly:newer};
}
function entryFromShell(config, id) {
    if (!object(config)) return {};
    var layout = config.bar && config.bar.layout || {};
    var sections = ['left','center','right'];
    for (var s=0; s<sections.length; s++) {
        var list = layout[sections[s]] || [];
        for (var i=0; i<list.length; i++) if (list[i] && list[i].id === id) return copy(list[i]);
    }
    var plugins = config.plugins || [];
    for (var j=0; j<plugins.length; j++) if (plugins[j] && plugins[j].id === id) return copy(plugins[j]);
    return {};
}
function mergedEntry(previous, values) {
    var out = object(previous) ? copy(previous) : {};
    Object.keys(keys).forEach(function(k) { if (values[k] !== undefined) out[keys[k]] = copy(values[k]); });
    return out;
}
function payload(raw) {
    var args = {}, errors = [];
    try {
        if (typeof raw === 'string' && raw.length > 32768) throw new Error('Payload exceeds 32 KiB');
        args = typeof raw === 'string' && raw ? JSON.parse(raw) : (object(raw) ? raw : {});
        if (!object(args)) throw new Error('Payload must be an object');
    } catch (e) { args = {}; errors.push('Invalid invocation payload; defaults used.'); }
    var out = {instrument:instruments.indexOf(args.instrument) >= 0 ? args.instrument : '',
        mode:args.mode === 'hold' ? 'hold' : 'toggle', monitor:safeText(args.monitor || args.screen,128),
        picker:args.picker === true, help:args.help === true, privacy:typeof args.privacy === 'boolean' ? args.privacy : null,
        focus:null, filters:{}, errors:errors};
    if (object(args.focus)) {
        var focus = {};
        ['key','type','processKey','groupKey','remoteKey','mountKey','deviceKey','audioKey','subsystem'].forEach(function(k) {
            if (typeof args.focus[k] === 'string') focus[k] = safeText(args.focus[k]);
        });
        if (Object.keys(focus).length) out.focus = focus;
    }
    if (object(args.filters)) {
        ['direction','protocol','state','emphasis','lens'].forEach(function(k) {
            if (typeof args.filters[k] === 'string') out.filters[k] = safeText(args.filters[k],32);
        });
    }
    return out;
}
if (typeof module !== 'undefined') module.exports = {instruments:instruments,defaults:defaults,keys:keys,normalize:normalize,entryFromShell:entryFromShell,mergedEntry:mergedEntry,payload:payload,safeText:safeText};
