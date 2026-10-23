// Dźwięki tablicy — syntezowane przez WebAudio, bez plików audio.
// Dzięki temu aplikacja dalej jest w pełni offline i nie rośnie o megabajty.
//
//   Sound.configure({ sound: true, volume: 0.6 });
//   Sound.play("start");
//
// Przeglądarki blokują dźwięk do pierwszego kliknięcia użytkownika, więc
// kontekst wznawiamy przy pierwszej interakcji, a tablica pokazuje wtedy
// podpowiedź (patrz board.js).

const Sound = (() => {
  let ctx = null;
  let enabled = true;
  let volume = 0.6;

  // Każdy dźwięk to lista nut: [częstotliwość Hz, start s, długość s, głośność, kształt]
  const PATTERNS = {
    start:   [[523, 0, .12, 1, "triangle"], [784, .10, .18, 1, "triangle"]],
    tick:    [[880, 0, .05, .5, "square"]],
    tickLast: [[1175, 0, .09, .8, "square"]],
    timeup:  [[392, 0, .16, .9, "sawtooth"], [294, .14, .28, .9, "sawtooth"]],
    reveal:  [[523, 0, .15, .9, "triangle"], [659, .08, .15, .9, "triangle"],
              [784, .16, .32, .9, "triangle"]],
    next:    [[660, 0, .07, .5, "sine"]],
    podium:  [[523, 0, .14, 1, "triangle"], [659, .13, .14, 1, "triangle"],
              [784, .26, .14, 1, "triangle"], [1046, .39, .5, 1, "triangle"]],
    roll:    [[1320, 0, .03, .35, "square"]],
    drawn:   [[659, 0, .1, .9, "triangle"], [988, .09, .4, .9, "triangle"]],
  };

  function audio() {
    const AC = window.AudioContext || window.webkitAudioContext;
    if (!AC) return null;
    if (!ctx) ctx = new AC();
    if (ctx.state === "suspended") ctx.resume();
    return ctx;
  }

  function note(ac, [freq, at, dur, gain, shape]) {
    const t0 = ac.currentTime + at;
    const osc = ac.createOscillator();
    const amp = ac.createGain();
    osc.type = shape || "sine";
    osc.frequency.setValueAtTime(freq, t0);
    // Miękka obwiednia — bez niej słychać trzaski na krańcach dźwięku.
    amp.gain.setValueAtTime(0.0001, t0);
    amp.gain.exponentialRampToValueAtTime(Math.max(0.0002, volume * gain * 0.35), t0 + 0.012);
    amp.gain.exponentialRampToValueAtTime(0.0001, t0 + dur);
    osc.connect(amp).connect(ac.destination);
    osc.start(t0);
    osc.stop(t0 + dur + 0.03);
  }

  return {
    configure(s) {
      if (!s) return;
      if (s.sound !== undefined) enabled = !!s.sound;
      if (s.volume !== undefined) volume = Math.min(1, Math.max(0, +s.volume));
    },
    get enabled() { return enabled; },
    // Czy dźwięk czeka na kliknięcie użytkownika (polityka autoodtwarzania).
    get blocked() { return enabled && (!ctx || ctx.state === "suspended"); },
    unlock() { const ac = audio(); if (ac) this.play("next"); },
    play(name) {
      if (!enabled) return;
      const pattern = PATTERNS[name];
      const ac = pattern && audio();
      if (!ac || ac.state !== "running") return;
      pattern.forEach(n => note(ac, n));
    },
  };
})();
