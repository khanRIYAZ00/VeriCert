import { useEffect, useState } from "react";
import { request, saveBlob } from "./api";
import { ThemeToggle } from "./theme";

function studentLabel(session) {
  return session?.user?.email || "Student";
}

function PortalShell({ children }) {
  return (
    <main className="student-page">
      <header className="student-topbar">
        <a className="wordmark" href="/">
          <span>V</span> VeriCert
        </a>
        <ThemeToggle />
      </header>
      <section className="student-card">{children}</section>
    </main>
  );
}

export default function StudentPortal({ session, setSession }) {
  const path = window.location.pathname.replace(/\/$/, "");
  if (path === "/forgot-password") return <ForgotPassword />;
  if (path === "/reset-password") return <ResetPassword />;
  if (session?.user?.must_change_password) {
    return (
      <ChangePassword
        session={session}
        onDone={() => {
          localStorage.removeItem("vericert-student-session");
          setSession(null);
        }}
      />
    );
  }
  if (session) return <Certificates session={session} setSession={setSession} />;
  return <StudentLogin setSession={setSession} />;
}

function StudentLogin({ setSession }) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function login(e) {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const result = await request("/auth/login", null, {
        method: "POST",
        body: JSON.stringify({ email, password }),
      });
      localStorage.setItem("vericert-student-session", JSON.stringify(result));
      setSession(result);
    } catch (err) {
      setError(err.message || "Unable to sign in");
    } finally {
      setLoading(false);
    }
  }

  return (
    <PortalShell>
      <p className="eyebrow">STUDENT PORTAL</p>
      <h1>Download your certificate</h1>
      <p>Sign in with your registered student email and password.</p>
      <form onSubmit={login}>
        <label>
          Student email
          <input
            autoFocus
            required
            type="email"
            autoComplete="username"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
          />
        </label>
        <label>
          Password
          <input
            type="password"
            required
            autoComplete="current-password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
        </label>
        {error && <p className="error">{error}</p>}
        <button disabled={loading}>{loading ? "Signing in..." : "Sign in"}</button>
      </form>
      <p className="login-footer">
        <a href="/forgot-password">Forgot your password?</a>
      </p>
    </PortalShell>
  );
}

function ChangePassword({ session, onDone }) {
  return (
    <PasswordForm
      title="Change your password"
      description="Choose a new password of at least 12 characters. You will need to sign in again."
      token={session.token}
      currentPasswordRequired
      onDone={onDone}
    />
  );
}

function PasswordForm({ title, description, token, currentPasswordRequired = false, onDone }) {
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(false);

  async function submit(e) {
    e.preventDefault();
    setError("");
    setMessage("");
    setLoading(true);
    try {
      if (token) {
        await request("/auth/change-password", token, {
          method: "POST",
          body: JSON.stringify({ current_password: currentPassword, new_password: newPassword }),
        });
      } else {
        await request("/auth/reset-password", null, {
          method: "POST",
          body: JSON.stringify({
            token: new URLSearchParams(window.location.search).get("token"),
            new_password: newPassword,
          }),
        });
      }
      setMessage("Password updated. Sign in using your new password.");
      if (onDone) onDone();
    } catch (err) {
      setError(err.message || "Unable to update password");
    } finally {
      setLoading(false);
    }
  }

  return (
    <PortalShell>
      <p className="eyebrow">ACCOUNT SECURITY</p>
      <h1>{title}</h1>
      <p>{description}</p>
      <form onSubmit={submit}>
        {currentPasswordRequired && (
          <label>
            Current password
            <input
              type="password"
              required
              autoComplete="current-password"
              value={currentPassword}
              onChange={(e) => setCurrentPassword(e.target.value)}
            />
          </label>
        )}
        <label>
          New password
          <input
            type="password"
            minLength={12}
            maxLength={128}
            required
            autoComplete="new-password"
            value={newPassword}
            onChange={(e) => setNewPassword(e.target.value)}
          />
        </label>
        {error && <p className="error">{error}</p>}
        {message && <p className="notice">{message}</p>}
        <button disabled={loading}>{loading ? "Updating..." : "Update password"}</button>
      </form>
      {!currentPasswordRequired && (
        <p className="login-footer">
          <a href="/download">Return to sign in</a>
        </p>
      )}
    </PortalShell>
  );
}

function ForgotPassword() {
  const [email, setEmail] = useState("");
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(false);

  async function submit(e) {
    e.preventDefault();
    setError("");
    setMessage("");
    setLoading(true);
    try {
      const result = await request("/auth/forgot-password", null, {
        method: "POST",
        body: JSON.stringify({ email }),
      });
      setMessage(result.message);
    } catch (err) {
      setError(err.message || "Unable to request password reset");
    } finally {
      setLoading(false);
    }
  }

  return (
    <PortalShell>
      <p className="eyebrow">ACCOUNT RECOVERY</p>
      <h1>Reset your password</h1>
      <p>Enter your registered email. If the account is active, we will send a reset link.</p>
      <form onSubmit={submit}>
        <label>
          Email
          <input required type="email" autoComplete="email" value={email} onChange={(e) => setEmail(e.target.value)} />
        </label>
        {error && <p className="error">{error}</p>}
        {message && <p className="notice">{message}</p>}
        <button disabled={loading}>{loading ? "Sending..." : "Send reset link"}</button>
      </form>
      <p className="login-footer">
        <a href="/download">Return to sign in</a>
      </p>
    </PortalShell>
  );
}

function ResetPassword() {
  return (
    <PasswordForm
      title="Choose a new password"
      description="Reset links expire after 30 minutes and can be used once."
    />
  );
}

function Certificates({ session, setSession }) {
  const [certificates, setCertificates] = useState([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [downloading, setDownloading] = useState(null);
  const [changingPassword, setChangingPassword] = useState(false);

  useEffect(() => {
    let alive = true;
    const loadCertificates = async () => {
      setLoading(true);
      setError("");
      try {
        const data = await request("/certificates/download", session.token);
        if (alive) setCertificates(Array.isArray(data) ? data : []);
      } catch (err) {
        if (alive) setError(err.message || "Unable to load certificates");
      } finally {
        if (alive) setLoading(false);
      }
    };
    loadCertificates();
    return () => {
      alive = false;
    };
  }, [session.token]);

  async function downloadCertificate(certificate) {
    setError("");
    setDownloading(certificate.id);
    try {
      const blob = await request(`/certificates/${certificate.id}/download`, session.token);
      saveBlob(blob, `${certificate.credential_id}.pdf`);
    } catch (err) {
      setError(err.message || "Download failed");
    } finally {
      setDownloading(null);
    }
  }

  function logout() {
    localStorage.removeItem("vericert-student-session");
    setSession(null);
  }

  if (changingPassword) {
    return (
      <ChangePassword
        session={session}
        onDone={() => {
          setChangingPassword(false);
          logout();
        }}
      />
    );
  }

  return (
    <PortalShell>
      <p className="eyebrow">STUDENT PORTAL</p>
      <h1>Your certificates</h1>
      <div className="student-meta">
        <p>
          Signed in as <strong>{studentLabel(session)}</strong>
          {session.user?.roll_number ? <> · Roll <strong>{session.user.roll_number}</strong></> : null}
        </p>
        <button className="secondary" type="button" onClick={() => setChangingPassword(true)}>
          Change password
        </button>
        <button className="secondary" type="button" onClick={logout}>
          Sign out
        </button>
      </div>
      {error && <p className="error">{error}</p>}
      {loading ? (
        <p className="muted">Loading your certificates...</p>
      ) : certificates.length === 0 ? (
        <p className="hint">No certificates have been issued for your account yet.</p>
      ) : (
        <div className="certificate-results">
          {certificates.map((certificate) => (
            <article className="certificate-choice" key={certificate.id}>
              <div>
                <strong>{certificate.event}</strong>
                <span>
                  {certificate.club}
                  {certificate.issue_date ? ` · Issued ${certificate.issue_date}` : ""}
                </span>
                <small>
                  {certificate.credential_id}
                  {certificate.status ? ` · ${certificate.status.replaceAll("_", " ")}` : ""}
                </small>
              </div>
              <button disabled={downloading === certificate.id} onClick={() => downloadCertificate(certificate)}>
                {downloading === certificate.id ? "Preparing..." : "Download PDF"}
              </button>
            </article>
          ))}
        </div>
      )}
    </PortalShell>
  );
}
