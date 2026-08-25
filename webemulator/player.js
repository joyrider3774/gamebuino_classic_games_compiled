// Standalone driver for the Simbuino4Web emulator core.
//
// Adapted from Simbuino4Web's own Scripts/Views/Simulation.js (Mark Feldman,
// "Myndale", MIT). That file was written for the ASP.NET MVC page it shipped
// with: it only ever loaded a .HEX through a file <input>. This version keeps
// the same emulator lifecycle but drives it from URL parameters instead, so a
// game can be linked to directly:
//
//   player.html?hex=../games/Tron.hex          load and run a game
//   &sd=../webemulator/sdcard.img              also mount an SD card image
//   &title=Tron                                label shown above the screen
//
// It also exposes window.SimbuinoPlayer, which the screenshot tool drives
// headlessly (run N frames, press a button, read the canvas back).

var simbuinoPlayer;

$(function () {

	function param(name) {
		var m = new RegExp('[?&]' + name + '=([^&]*)').exec(window.location.search);
		return m ? decodeURIComponent(m[1].replace(/\+/g, ' ')) : null;
	}

	// Gamebuino Classic has a d-pad plus A/B/C. Arrow keys and Simbuino's
	// original ESDF block both work, so either hand position is fine.
	var KEYMAP = {
		38: 'Up',    69: 'Up',
		40: 'Down',  68: 'Down',
		37: 'Left',  83: 'Left',
		39: 'Right', 70: 'Right',
		88: 'A', 75: 'A', 13: 'A',
		90: 'B', 76: 'B', 8:  'B',
		67: 'C', 82: 'C'
	};

	var Player = Class.create({

		ctor: function () {
			var self = this;
			this.Canvas = document.getElementById('canvas');
			this.Context = this.Canvas.getContext('2d', { willReadFrequently: true });
			this.Context.mozImageSmoothingEnabled = false;
			this.Context.webkitImageSmoothingEnabled = false;
			this.Context.imageSmoothingEnabled = false;

			AtmelContext.Init();
			AtmelProcessor.Init();
			ADC.Init();
			Buttons.Init();
			SPI.Init();
			USART.Init();
			EEPROM.Init();
			Lcd.Init(this.Context);
			SdDevice.Init();
			HexDecoder.Decode(Bootloader);

			this.FrameRate = 60;
			this.CyclesPerFrame = Math.floor(AtmelProcessor.ClockSpeed / this.FrameRate);
			this.Loaded = false;
			this.FramesRun = 0;
			this.Held = {};

			// Audio is optional: the screenshot runs are headless and muted,
			// and a page that never gets a user gesture cannot start audio at
			// all. Failing to build it must not stop the emulator.
			try {
				this.AudioPlayer = AudioPlayer.create();
			} catch (e) {
				this.AudioPlayer = null;
			}

			window.addEventListener('keydown', function (e) { self.OnKey(e, true); });
			window.addEventListener('keyup', function (e) { self.OnKey(e, false); });
			this.BindTouch();

			$('#reset').click(function () { self.Reset(); });
			$('#sound').click(function () { self.ToggleSound(); });
			$('#gray').click(function () { self.SetPersistence(!Lcd.Persistence); });

			// Gamebuino's GRAY is a pixel toggled every frame on a one-bit
			// panel, so it needs the LCD's response time simulated to read as a
			// mid-tone rather than a flicker. On by default here (upstream's
			// standalone emulator defaults it off); the choice sticks per
			// browser, and ?gray=0 overrides it for a single link.
			var pref = param('gray');
			if (pref === null) {
				try { pref = localStorage.getItem('simbuino.gray'); } catch (e) { pref = null; }
			}
			this.SetPersistence(pref === null ? true
			                                  : (pref === '1' || pref === 'on' || pref === 'true'));

			setInterval(function () { self.Update(); }, 1000 / this.FrameRate);
		},

		// ---- emulator lifecycle -------------------------------------------

		Boot: function (hexText) {
			this.Firmware = hexText.replace(/\r/g, '').split('\n');
			return this.Reset();
		},

		Reset: function () {
			if (!this.Firmware)
				return false;
			AtmelContext.Reset();
			HexDecoder.Decode(Bootloader);
			this.Loaded = HexDecoder.Decode(this.Firmware);
			AtmelProcessor.InitInstrTable();
			Lcd.Reset();
			Buttons.Reset();
			this.FramesRun = 0;
			return this.Loaded;
		},

		Update: function () {
			if (!this.Loaded)
				return;
			AtmelProcessor.RunTo(AtmelContext.Clock + this.CyclesPerFrame);
			this.FramesRun++;
		},

		// ---- input ---------------------------------------------------------

		SetButton: function (name, down) {
			var b = Buttons[name];
			if (b)
				b.call(Buttons).set(down);
		},

		OnKey: function (e, down) {
			var name = KEYMAP[e.keyCode];
			if (!name)
				return;
			e.preventDefault();
			this.SetButton(name, down);
		},

		// Tap targets for phones; each .pad element names its button in
		// data-btn. Pointer events cover mouse and touch in one path.
		BindTouch: function () {
			var self = this;
			$('.pad').each(function () {
				var el = this;
				var name = el.getAttribute('data-btn');
				function down(e) { e.preventDefault(); el.classList.add('on'); self.SetButton(name, true); }
				function up(e) { e.preventDefault(); el.classList.remove('on'); self.SetButton(name, false); }
				el.addEventListener('pointerdown', down);
				el.addEventListener('pointerup', up);
				el.addEventListener('pointercancel', up);
				el.addEventListener('pointerleave', up);
			});
		},

		SetPersistence: function (on) {
			Lcd.Persistence = !!on;
			Lcd.Reset();
			$('#gray').text('Grey blend: ' + (on ? 'on' : 'off'));
			try { localStorage.setItem('simbuino.gray', on ? '1' : '0'); } catch (e) { }
		},

		ToggleSound: function () {
			if (!this.AudioPlayer || !this.AudioPlayer.Context)
				return;
			var ctx = this.AudioPlayer.Context;
			if (ctx.state === 'running') {
				ctx.suspend();
				$('#sound').text('Sound: off');
			} else {
				ctx.resume();
				$('#sound').text('Sound: on');
			}
		}
	});

	function status(msg, isError) {
		$('#status').text(msg || '').toggleClass('error', !!isError);
	}

	function fetchText(url) {
		return fetch(url).then(function (r) {
			if (!r.ok) throw new Error(r.status + ' ' + r.statusText);
			return r.text();
		});
	}

	simbuinoPlayer = Player.create();

	// ---- public hook used by the screenshot tool ---------------------------
	window.SimbuinoPlayer = {
		ready: false,
		error: null,
		get frames() { return simbuinoPlayer.FramesRun; },
		canvas: function () { return document.getElementById('canvas'); },
		reset: function () { return simbuinoPlayer.Reset(); },
		// used by the screenshot tool: grey areas otherwise land fully on or
		// fully off depending which half of the dither the frame caught
		setGray: function (on) { simbuinoPlayer.SetPersistence(on); },
		// hold a button down for `frames` emulated frames, then release
		press: function (name, frames) {
			simbuinoPlayer.SetButton(name, true);
			var held = frames || 6;
			var target = simbuinoPlayer.FramesRun + held;
			return new Promise(function (resolve) {
				var t = setInterval(function () {
					if (simbuinoPlayer.FramesRun >= target) {
						clearInterval(t);
						simbuinoPlayer.SetButton(name, false);
						resolve();
					}
				}, 8);
			});
		},
		// resolve once `n` more emulated frames have been executed
		runFrames: function (n) {
			var target = simbuinoPlayer.FramesRun + n;
			return new Promise(function (resolve) {
				var t = setInterval(function () {
					if (simbuinoPlayer.FramesRun >= target) {
						clearInterval(t);
						resolve();
					}
				}, 8);
			});
		}
	};

	// ---- load whatever the URL asked for -----------------------------------
	var title = param('title');
	if (title)
		document.title = title + ' - Simbuino4Web';
	$('#title').text(title || '');

	var sd = param('sd');
	var hex = param('hex');

	var sdReady = !sd ? Promise.resolve() : fetch(sd)
		.then(function (r) {
			if (!r.ok) throw new Error(r.status + ' ' + r.statusText);
			return r.arrayBuffer();
		})
		.then(function (buf) { SdDevice.ReadBuffer = new Uint8Array(buf); })
		.catch(function (e) { status('SD card image failed to load: ' + e.message, true); });

	if (!hex) {
		status('No game specified. Add ?hex=<url> to the address.');
	} else {
		sdReady.then(function () { return fetchText(hex); })
			.then(function (text) {
				if (!simbuinoPlayer.Boot(text))
					throw new Error('not a valid Intel HEX image for this device');
				window.SimbuinoPlayer.ready = true;
				status('');
			})
			.catch(function (e) {
				window.SimbuinoPlayer.error = e.message;
				status('Could not load ' + hex + ' - ' + e.message, true);
			});
	}

	// A local file can still be dropped in, which is handy for testing a build
	// that is not part of this collection.
	$('#hexInput').change(function () {
		var file = this.files[0];
		if (!file) return;
		var reader = new FileReader();
		reader.onload = function () {
			if (simbuinoPlayer.Boot(reader.result)) {
				status('');
				$('#title').text(file.name);
			} else {
				status('Could not load ' + file.name, true);
			}
		};
		reader.readAsText(file);
	});
});
