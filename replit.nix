{pkgs}: {
  deps = [
    pkgs.ffmpeg
    pkgs.libsodium
    pkgs.libxcrypt
    pkgs.postgresql
    pkgs.openssl
  ];
}
