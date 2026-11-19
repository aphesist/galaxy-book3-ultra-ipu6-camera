# Galaxy Book3 Ultra webcam through Intel's IPU6 pipeline (AIQ)

Arch Linux packages that run the Samsung Galaxy Book3 Ultra's OV02C10 webcam
through Intel's own image pipeline (IPU6 PSYS + AIQ 3A, via libcamhal), the
same kind of processing Windows uses, instead of libcamera's software ISP.

Compared with the software ISP the picture has real contrast and black
levels and much less grain, at full frame rate, in every PipeWire app
(Firefox/Zen, Chromium, Meet, OBS...).

Tested on: Galaxy Book3 Ultra (960XFH), Raptor Lake IPU6 (`ipu6ep`), Arch
Linux, kernel 7.3, PipeWire 1.6, WirePlumber 0.5.

## Requirements

The OV02C10 needs an out-of-tree driver first: the board feeds it 26 MHz and
mainline only accepts 19.2 MHz. Install it from
[galaxy-book3-ultra-linux](https://github.com/aphesist/galaxy-book3-ultra-linux)
(webcam section), which also sets `rotation=180`. Check that the camera works
with the stock pipeline before switching.

## What's in here

| Folder | Package | What |
|---|---|---|
| `packages/ipu6-psys-dkms` | `ipu6-psys-dkms` | Intel's PSYS kernel module only (DKMS). AUR `intel-ipu6-dkms-git` also installs Intel's own `ov02c10` driver, which overrides the 26 MHz one |
| `packages/intel-ipu6-camera-bin` | `intel-ipu6-camera-bin` | Intel's closed AIQ/ISP libraries from [ipu6-camera-bins](https://github.com/intel/ipu6-camera-bins). The AUR package of this name has an empty git repo. No firmware: `linux-firmware-intel` ships it |
| `packages/intel-ipu6-camera-hal` | `intel-ipu6-camera-hal-git` | Intel's [libcamhal](https://github.com/intel/ipu6-camera-hal) for `ipu6ep`, with fixes below |
| `packages/libcamera-ipu6` | `libcamera-ipu6`, `-ipa`, `-tools` | [kervel's IPU6 pipeline handler](https://github.com/kervel/libcamera/tree/ipu6-pipeline-handler) (based on the AUR package by Stick), plus `0003-ipu6-add-ov02c10.patch` |
| `config/61-ipu6-ov02c10.conf` | | Image tuning, read by PipeWire/WirePlumber |

Fixes needed for this laptop:

- HAL: the OV02C10 sits on CSI-2 port 0, which Intel's profile doesn't list,
  so the HAL never detected the sensor.
- HAL: the sensor is mounted upside down. Intel's HAL ignores the driver's
  `rotation=180`, so the config enables the sensor's own H/V flips
  (`ov02c10-flip.py`). The 26 MHz driver keeps the Bayer order when flipped.
- HAL: uses the `OV02C10_1SG204N3` tuning; the default `1BG203N3` looked worse.
- libcamera: OV02C10 sensor helper (from libcamera patchwork 28174) and sensor
  properties, and 1920x1080 output.
- libcamera: the pipeline queued 2 buffers to a HAL that keeps up to 5 in
  flight, dropping about 2 of every 3 frames (6.7 fps). Now 6.
- libcamera: `IPU6_*` environment variables to tune noise reduction,
  sharpness, white balance and frame rate (see Tuning).
- udev: the PSYS permission rule is installed as `70-` instead of `99-`. As
  `99-` its `uaccess` tag comes after `73-seat-late.rules`, the user never gets
  access to `/dev/ipu-psys0`, and streams fail with "Failed to configure camera".

Every package pins the source commit it was tested with. The AUR-named
packages carry `epoch=1`, so yay won't replace them with the AUR versions.

Intel publishes no tuning for this exact camera module, so the pipeline
borrows the OV02C10 tuning of an Alder Lake laptop. Out of the box it
over-smooths and has a slight green cast; the settings in
`config/61-ipu6-ov02c10.conf` correct that.

## Install

```sh
git clone https://github.com/aphesist/galaxy-book3-ultra-ipu6-camera
cd galaxy-book3-ultra-ipu6-camera/packages

(cd ipu6-psys-dkms && makepkg -si)
(cd intel-ipu6-camera-bin && makepkg -si)
(cd intel-ipu6-camera-hal && makepkg -si)
# Replaces libcamera, libcamera-ipa and libcamera-tools; answer y to removing them.
(cd libcamera-ipu6 && makepkg -s && sudo pacman -U \
  libcamera-ipu6-1:*-x86_64.pkg.tar.zst \
  libcamera-ipu6-ipa-1:*-x86_64.pkg.tar.zst \
  libcamera-ipu6-tools-1:*-x86_64.pkg.tar.zst)

mkdir -p ~/.config/environment.d
cp ../config/61-ipu6-ov02c10.conf ~/.config/environment.d/
reboot
```

Back-up the stock `libcamera*` packages from `/var/cache/pacman/pkg` first
if you want an easy way back.

Check after the reboot:

```sh
lsmod | grep intel_ipu6_psys          # PSYS loaded
getfacl /dev/ipu-psys0 | grep user:   # your user has rw
wpctl status                          # Video: ov02c10-uf [libcamera]
cam -l                                # 1: Internal front camera (ipu6-ov02c10-uf-0)
```

Firefox and Firefox-based browsers (Zen, LibreWolf) need
`media.webrtc.camera.allow-pipewire = true` in `about:config` (or `user.js`);
otherwise they scan the raw IPU6 V4L2 nodes and list 30+ "ipu6" cameras that
don't work.

## Tuning

Edit `~/.config/environment.d/61-ipu6-ov02c10.conf`, then log out and back in
(or `systemctl --user restart wireplumber`):

| Variable | Range | Default here | Effect |
|---|---|---|---|
| `IPU6_NR_SPATIAL` | -100..100 | -100 | spatial noise reduction (lower = sharper, more grain) |
| `IPU6_NR_TEMPORAL` | -100..100 | -100 | temporal noise reduction (lower = less smearing on motion) |
| `IPU6_NR_OVERALL` | -100..100 | unset | overall noise reduction |
| `IPU6_SHARPNESS` | -100..100 | 70 | edge enhancement |
| `IPU6_AWB_SHIFT` | `r,g,b`, 0..255 | `128,104,128` | white balance shift; equal = neutral, lower g = less green |
| `IPU6_FPS_RANGE` | `min,max` | unset (auto) | auto drops to ~20 fps in dim light for a brighter image; `30,30` is smooth but darker |

## Troubleshooting

- Camera listed but apps load forever: WirePlumber started before your user
  could open `/dev/ipu-psys0` and Intel's HAL doesn't retry. Check the
  `getfacl` line above, then `systemctl --user restart wireplumber`.
- Upside down or mirrored: the flips live in
  `/etc/camera/ipu6ep/sensors/ov02c10-uf.xml` (`V4L2_CID_VFLIP` /
  `V4L2_CID_HFLIP` controls); restart WirePlumber after editing.
- Don't probe the camera with `cam` while an app is streaming.

## Roll back

```sh
sudo pacman -U /var/cache/pacman/pkg/libcamera{,-ipa,-tools}-0.7.2-*.pkg.tar.zst   # your stock versions
sudo pacman -Rns intel-ipu6-camera-hal-git intel-ipu6-camera-bin ipu6-psys-dkms
rm ~/.config/environment.d/61-ipu6-ov02c10.conf
reboot
```

## Credits and licenses

- Intel: [ipu6-drivers](https://github.com/intel/ipu6-drivers) (GPL-2.0),
  [ipu6-camera-hal](https://github.com/intel/ipu6-camera-hal) (Apache-2.0),
  [ipu6-camera-bins](https://github.com/intel/ipu6-camera-bins) (Intel
  proprietary, downloaded at build time, not redistributed here).
- [kervel/libcamera](https://github.com/kervel/libcamera) IPU6 pipeline
  handler, AUR `libcamera-ipu6` by Stick (patches 0001/0002, udev rule,
  systemd drop-ins, `wait-libcamhal-shm.c`).
- OV02C10 sensor helper based on libcamera patchwork 28174 by Martin Neiva de
  Carvalho.

Patches are under the license of the project they apply to. Everything else
here (PKGBUILDs, scripts, docs) is MIT, see `LICENSE`.
