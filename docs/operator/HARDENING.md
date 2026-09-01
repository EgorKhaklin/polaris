# HARDENING.md: the host under Polaris

[`deploy/linux/install.sh`](../../deploy/linux/install.sh) configures Polaris.
This page is the operating system around it: what to do on a fresh Debian,
Ubuntu, or RHEL-family server before it carries real identity data, as
copy-paste commands. Polaris's own container hardening (capabilities dropped,
`no-new-privileges`, digest-pinned images, TLS on every hop, secrets as mounted
files) is already in the compose file; nothing here duplicates it.

Do these in order. Each block has a Debian/Ubuntu form and a RHEL form where
they differ.

## 1. Accounts and SSH

Key-only, no root login, no passwords.

```bash
sudo adduser ops && sudo usermod -aG sudo ops          # RHEL: useradd -m ops && usermod -aG wheel ops
sudo install -m 0700 -d /home/ops/.ssh && sudo cp ~/.ssh/authorized_keys /home/ops/.ssh/ && sudo chown -R ops:ops /home/ops/.ssh
sudo tee /etc/ssh/sshd_config.d/10-polaris.conf >/dev/null <<'EOF'
PasswordAuthentication no
KbdInteractiveAuthentication no
PermitRootLogin no
MaxAuthTries 3
AllowUsers ops
EOF
sudo systemctl reload ssh 2>/dev/null || sudo systemctl reload sshd
```

Test a second session as `ops` before closing the first.

## 2. Updates

Security updates apply themselves; you reboot on your schedule.

```bash
# Debian/Ubuntu
sudo apt-get install -y unattended-upgrades && sudo dpkg-reconfigure -f noninteractive unattended-upgrades
# RHEL family
sudo dnf install -y dnf-automatic && sudo sed -i 's/^apply_updates = .*/apply_updates = yes/' /etc/dnf/automatic.conf && sudo systemctl enable --now dnf-automatic.timer
```

Docker Engine comes from Docker's repository (the installer added it with a
verified key), so it is covered by the same mechanism.

## 3. Firewall, and how Docker relates to it

Only 22, 80, 443 (TCP) and 443 (UDP, HTTP/3) are open. The stack publishes
only 80 and 443; Postgres, Redis, pgbouncer, and the app itself are on the
internal compose network, never on the host.

```bash
# Debian/Ubuntu (ufw)
sudo apt-get install -y ufw && sudo ufw default deny incoming && sudo ufw default allow outgoing
sudo ufw allow 22/tcp && sudo ufw allow 80/tcp && sudo ufw allow 443/tcp && sudo ufw allow 443/udp && sudo ufw --force enable
# RHEL family (firewalld)
sudo systemctl enable --now firewalld
sudo firewall-cmd --permanent --add-service=ssh --add-service=http --add-service=https && sudo firewall-cmd --permanent --add-port=443/udp && sudo firewall-cmd --reload
```

Docker writes its own iptables rules for published ports, which bypass ufw.
That is harmless as long as compose publishes only 80/443, which it does. Do
not add `ports:` to any service expecting ufw to hide it. If you need
`/metrics` reachable by a monitoring host, do it in the Caddyfile with a source
IP allow list, not by publishing the app port.

## 4. Time

TLS validity, ACME, WebAuthn, and the anchoring chain all assume a correct
clock.

```bash
sudo apt-get install -y chrony || sudo dnf install -y chrony
sudo systemctl enable --now chrony 2>/dev/null || sudo systemctl enable --now chronyd
chronyc tracking | head -3
```

## 5. The Docker daemon

No remote API, no privilege creep, containers survive a daemon restart, logs
bounded (compose already sets per-container log limits).

```bash
sudo tee /etc/docker/daemon.json >/dev/null <<'EOF'
{
  "live-restore": true,
  "no-new-privileges": true,
  "log-driver": "json-file",
  "log-opts": { "max-size": "10m", "max-file": "5" }
}
EOF
sudo systemctl restart docker && sudo systemctl restart polaris
```

Never enable the TCP socket (`-H tcp://`). Membership of the `docker` group is
root-equivalent; keep it empty and use sudo.

## 6. Filesystem and permissions

```bash
sudo chown -R root:root /opt/polaris && sudo chmod 0700 /opt/polaris/polaris_web/secrets
sudo chmod 0600 /etc/polaris/polaris.env
sudo chmod 0750 /var/backups/polaris
```

Give `/var/lib/docker` its own volume so a full disk from a runaway log or a
backup pile-up cannot take the OS down with it, and mount `/tmp` with
`nodev,nosuid,noexec` (`/etc/fstab`, then `sudo mount -o remount /tmp`). Enable
full-disk encryption at provisioning time; what is plaintext on disk is in
[`ENCRYPTION-AT-REST.md`](ENCRYPTION-AT-REST.md).

## 7. Kernel

```bash
sudo tee /etc/sysctl.d/60-polaris.conf >/dev/null <<'EOF'
net.ipv4.conf.all.accept_redirects = 0
net.ipv4.conf.all.send_redirects = 0
net.ipv4.conf.all.accept_source_route = 0
net.ipv4.tcp_syncookies = 1
kernel.kptr_restrict = 2
kernel.dmesg_restrict = 1
fs.protected_symlinks = 1
fs.protected_hardlinks = 1
EOF
sudo sysctl --system >/dev/null
```

`net.ipv4.ip_forward` stays 1; Docker needs it.

## 8. Auditing

Know when the secrets or the configuration are touched.

```bash
sudo apt-get install -y auditd || sudo dnf install -y audit
sudo tee /etc/audit/rules.d/polaris.rules >/dev/null <<'EOF'
-w /opt/polaris/polaris_web/secrets -p rwa -k polaris-secrets
-w /etc/polaris -p wa -k polaris-config
-w /etc/systemd/system/polaris.service -p wa -k polaris-unit
EOF
sudo augenrules --load && sudo systemctl enable --now auditd
```

Application-level audit (issuance, revocation, verification, operator
authentication) is the append-only audit-of-record inside the database (C1);
this is the host-level complement.

## 9. Brute force

```bash
sudo apt-get install -y fail2ban || sudo dnf install -y fail2ban
sudo tee /etc/fail2ban/jail.d/polaris.local >/dev/null <<'EOF'
[sshd]
enabled = true
maxretry = 4
bantime = 1h
EOF
sudo systemctl enable --now fail2ban
```

Login rate limiting for the application itself is inside Polaris (per-IP and
per-account, Redis-backed) and at the Caddy edge (`rate_limit`).

## 10. Metrics exposure

`/metrics` carries the duress signal. It must be reachable only by your
monitoring host ([`../../deploy/observability/README.md`](../../deploy/observability/README.md)
"Access control"). The shipped Caddyfile does not expose it publicly; if you add
a monitoring route, restrict it by source IP there.

## 11. Backups off the host

`/var/backups/polaris` is on the same disk as the database. Either copy the
tarballs off-host on a schedule, or enable the pgBackRest S3 repository, which
is configured by env alone and drilled in CI ([`DR.md`](DR.md)).

## 12. RHEL specifics

- SELinux enforcing is the default and is good; Docker bind mounts under
  `/opt/polaris` may need labels: `sudo chcon -Rt svirt_sandbox_file_t /opt/polaris`.
- `firewalld` and Docker cooperate better than ufw does, but the same rule
  applies: publish nothing beyond 80/443.

## Verify

```bash
sudo ss -tulpn | grep LISTEN              # expect 22, 80, 443 (tcp), 443 (udp), and docker-proxy for those only
sudo ufw status verbose 2>/dev/null || sudo firewall-cmd --list-all
systemctl is-active polaris chrony auditd fail2ban 2>/dev/null
curl -fsS https://$POLARIS_DOMAIN/api/health | python3 -m json.tool | head -20
```

Then the operations checklist in [`OPERATIONS.md`](OPERATIONS.md), and the
first backup restore drill in [`DR.md`](DR.md), before the host goes live.
