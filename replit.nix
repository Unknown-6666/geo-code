{pkgs}: {
  deps = [
    pkgs.ffmpeg-full
    pkgs.ffmpeg
    pkgs.libsodium
    pkgs.libxcrypt
    pkgs.postgresql
    pkgs.openssl
  ];
}
