"""Ativa SSL via certbot."""
import paramiko

HOST = "72.62.10.198"
USER = "root"
PASS = "4l.PJ0(Z,Yp/iCc7bk/K"

def run(client, cmd, timeout=120):
    print(f"\n$ {cmd[:100]}")
    _, stdout, stderr = client.exec_command(cmd, timeout=timeout, get_pty=True)
    out = stdout.read().decode(errors="replace")
    rc = stdout.channel.recv_exit_status()
    for line in (out).splitlines():
        if line.strip():
            print(line)
    return rc, out

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(HOST, username=USER, password=PASS, timeout=15)
print("Conectado")

rc, _ = run(client, (
    "certbot --nginx "
    "-d crystalpresentes.com.br "
    "-d www.crystalpresentes.com.br "
    "--non-interactive --agree-tos "
    "--email lojacrystalpresentes@hotmail.com "
    "--redirect"
), timeout=120)

if rc == 0:
    print("\nSSL ativo! https://crystalpresentes.com.br")
else:
    print("\nErro no certbot — verificando DNS:")
    run(client, "dig +short crystalpresentes.com.br A")

client.close()
