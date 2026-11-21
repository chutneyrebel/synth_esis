/* Phase 12G: external UI descriptions for Schwung Remote UI.
 * Presentation data only. No preset keys, engine defaults or native hierarchy.
 * The manager serves sibling assets from the module directory. */
(function (global) {
  'use strict';
  const controls = [
    { key: 'vel_spec', label: 'Velocity Shift', help: 'How note velocity bends spectral Shift. Constant throughout each held note.' },
    { key: 'vel_f', label: 'Velocity Fold', help: 'How note velocity shapes the Fold attack and decay of each voice.' },
    { key: 'vel_s', label: 'Velocity Scramble', help: 'How note velocity shapes the Scramble attack and decay of each voice.' }
  ];
  const spectral = [
    { key: 'osc1_spectral_shift', label: 'OSC 1 Shift', help: 'Manual spectral Shift, also influenced by LFO and per-note velocity.' },
    { key: 'osc1_spectral_fold', label: 'OSC 1 Fold', help: 'Manual spectral Fold, plus LFO and velocity attack.' },
    { key: 'osc1_spectral_scramble', label: 'OSC 1 Scramble', help: 'Manual Scramble, plus LFO and velocity attack.' },
    { key: 'osc2_spectral_shift', label: 'OSC 2 Shift', help: 'Manual spectral Shift on oscillator 2.' },
    { key: 'osc2_spectral_fold', label: 'OSC 2 Fold', help: 'Manual spectral Fold on oscillator 2.' },
    { key: 'osc2_spectral_scramble', label: 'OSC 2 Scramble', help: 'Manual spectral Scramble on oscillator 2.' }
  ];
  global.synthEsisUi = Object.freeze({
    version: 1,
    velocity: Object.freeze(controls.map(x => Object.freeze(x))),
    spectral: Object.freeze(spectral.map(x => Object.freeze(x)))
  });
})(typeof window !== 'undefined' ? window : globalThis);
