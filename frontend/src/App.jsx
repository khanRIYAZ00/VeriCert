import { useEffect, useRef, useState } from "react";
import { API, request, saveBlob } from "./api";
import StudentPortal from "./StudentPortal";
import { ThemeProvider, ThemeToggle } from "./theme";

const builtins = ["recipient_name", "roll_no", "credential_id", "issue_date", "club", "event", "qr"];

export default function App() {
  return (
    <ThemeProvider>
      <AppRoutes />
    </ThemeProvider>
  );
}

function AppRoutes() {
  const [session, setSession] = useState(() => JSON.parse(localStorage.getItem("vericert-session") || "null"));
  const [studentSession, setStudentSession] = useState(() => JSON.parse(localStorage.getItem("vericert-student-session") || "null"));
  const path = window.location.pathname.replace(/\/$/, "") || "/";

  if (path === "/download" || path === "/forgot-password" || path === "/reset-password") {
    return <StudentPortal session={studentSession} setSession={setStudentSession} />;
  }

  if (session?.user?.must_change_password) {
    return (
      <AdminPasswordChange
        session={session}
        onDone={() => {
          localStorage.removeItem("vericert-session");
          setSession(null);
        }}
      />
    );
  }

  return session ? (
    <Workspace
      session={session}
      logout={() => {
        localStorage.removeItem("vericert-session");
        setSession(null);
      }}
    />
  ) : (
    <Login
      onLogin={(value) => {
        if (value.user.role === "platform_admin" || value.user.role === "club_admin") {
          localStorage.setItem("vericert-session", JSON.stringify(value));
          setSession(value);
        } else {
          localStorage.setItem("vericert-student-session", JSON.stringify(value));
          window.location.assign("/download");
        }
      }}
    />
  );
}

function AdminPasswordChange({ session, onDone }) {
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function submit(e) {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      await request("/auth/change-password", session.token, {
        method: "POST",
        body: JSON.stringify({ current_password: currentPassword, new_password: newPassword }),
      });
      onDone();
    } catch (err) {
      setError(err.message || "Unable to update password");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="login">
      <ThemeToggle className="theme-toggle-fixed" />
      <section>
        <p className="eyebrow">ACCOUNT SECURITY</p>
        <h1>Change your password</h1>
        <p>A password change is required before continuing. Choose at least 12 characters.</p>
        <form onSubmit={submit}>
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
          <button disabled={loading}>{loading ? "Updating..." : "Update password"}</button>
        </form>
      </section>
    </main>
  );
}

function Login({ onLogin }) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function submit(e) {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const result = await request("/auth/login", null, {
        method: "POST",
        body: JSON.stringify({ email, password }),
      });
      onLogin(result);
    } catch (err) {
      setError(err.message || "Login failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="login">
      <ThemeToggle className="theme-toggle-fixed" />
      <section>
        <div className="login-mark">V</div>
        <p className="eyebrow">VERIFIABLE CREDENTIALS</p>
        <h1>Welcome to VeriCert</h1>
        <p>Create, issue, and independently verify event certificates.</p>

        <form onSubmit={submit}>
          <label>
            Email
            <input autoComplete="username" value={email} onChange={(e) => setEmail(e.target.value)} />
          </label>
          <label>
            Password
            <input type="password" autoComplete="current-password" value={password} onChange={(e) => setPassword(e.target.value)} />
          </label>
          {error && <p className="error">{error}</p>}
          <button disabled={loading}>{loading ? "Signing in..." : "Sign in"}</button>
        </form>

        <p className="login-footer">
          Students can collect certificates from the{" "}
          <a href="/download">download portal</a>.
          {" "}
          <a href="/forgot-password">Forgot password?</a>
        </p>
      </section>
    </main>
  );
}

function Workspace({ session, logout }) {
  const [clubs, setClubs] = useState([]);
  const [club, setClub] = useState(null);
  const [view, setView] = useState("events");
  const [message, setMessage] = useState("");

  const loadClubs = async () => {
    const data = await request("/clubs", session.token);
    setClubs(data);
    setClub((current) => data.find((item) => item.id === current?.id) || data[0] || null);
  };

  useEffect(() => {
    let alive = true;
    request("/clubs", session.token)
      .then((data) => {
        if (!alive) return;
        setClubs(data);
        setClub((current) => data.find((item) => item.id === current?.id) || data[0] || null);
      })
      .catch((error) => {
        if (alive) setMessage(error.message || "Unable to load clubs");
      });
    return () => {
      alive = false;
    };
  }, [session.token]);

  const nav = [
    ["events", "Events"],
    ["templates", "Templates"],
    ["issue", "Issue"],
    ["history", "History"],
    ...(session.user.role === "platform_admin" ? [["students", "Students"]] : []),
  ];

  return (
    <div className="shell">
      <aside>
        <div className="brand">
          <span>V</span>
          <strong>VeriCert</strong>
        </div>

        <button
          className="club-add"
          onClick={async () => {
            const name = prompt("Club name");
            if (!name) return;
            try {
              await request("/clubs", session.token, {
                method: "POST",
                body: JSON.stringify({ name }),
              });
              await loadClubs();
            } catch (error) {
              setMessage(error.message || "Unable to create club");
            }
          }}
        >
          + New club
        </button>

        <div className="club-list">
          {clubs.map((item) => (
            <button key={item.id} className={club?.id === item.id ? "selected" : ""} onClick={() => setClub(item)}>
              {item.name}
            </button>
          ))}
        </div>

        <nav>
          {nav.map(([id, label]) => (
            <button key={id} className={view === id ? "active" : ""} onClick={() => setView(id)}>
              {label}
            </button>
          ))}
        </nav>

        <a className="student-link" href="/download">
          Student download portal
        </a>
        <button className="logout" onClick={logout}>
          Sign out
        </button>
      </aside>

      <main className="workspace">
        <header>
          <div>
            <p className="eyebrow">{club?.name || "NO CLUB SELECTED"}</p>
            <h1>{view[0].toUpperCase() + view.slice(1)}</h1>
          </div>
          <div className="workspace-tools">
            <p className="account">{session.user.email}</p>
            <ThemeToggle />
          </div>
        </header>

        {message && <p className="notice">{message}</p>}
        {view === "students" && session.user.role === "platform_admin" ? (
          <StudentManagement token={session.token} notify={setMessage} />
        ) : club ? (
          <Content view={view} club={club} token={session.token} notify={setMessage} />
        ) : (
          <EmptyState />
        )}
      </main>
    </div>
  );
}

function EmptyState() {
  return (
    <section className="empty">
      <h2>Create your first club</h2>
      <p>Clubs own the certificate designs, events, and issuance records they manage.</p>
    </section>
  );
}

function Content({ view, ...props }) {
  if (view === "templates") return <Templates {...props} />;
  if (view === "events") return <Events {...props} />;
  if (view === "issue") return <Issue {...props} />;
  return <History {...props} />;
}

function StudentManagement({ token, notify }) {
  const [students, setStudents] = useState([]);
  const [email, setEmail] = useState("");
  const [rollNumber, setRollNumber] = useState("");
  const [emailVerified, setEmailVerified] = useState(false);
  const [temporaryPassword, setTemporaryPassword] = useState("");
  const [error, setError] = useState("");

  const loadStudents = async () => {
    const data = await request("/admin/students", token);
    setStudents(data);
  };

  useEffect(() => {
    let alive = true;
    request("/admin/students", token)
      .then((data) => {
        if (alive) setStudents(data);
      })
      .catch((err) => {
        if (alive) setError(err.message || "Unable to load student accounts");
      });
    return () => {
      alive = false;
    };
  }, [token]);

  async function createStudent(e) {
    e.preventDefault();
    setError("");
    setTemporaryPassword("");
    try {
      const result = await request("/admin/students", token, {
        method: "POST",
        body: JSON.stringify({ email, roll_number: rollNumber, email_verified: emailVerified }),
      });
      setEmail("");
      setRollNumber("");
      setEmailVerified(false);
      setTemporaryPassword(result.temporary_password);
      notify("Account created. Copy the temporary password now; it is shown only once.");
      await loadStudents();
    } catch (err) {
      setError(err.message || "Unable to create student account");
    }
  }

  async function deactivateStudent(student) {
    if (!window.confirm(`Deactivate ${student.email}? Their current sessions will be revoked.`)) return;
    setError("");
    try {
      await request(`/admin/students/${student.id}/deactivate`, token, { method: "POST" });
      await loadStudents();
    } catch (err) {
      setError(err.message || "Unable to deactivate student");
    }
  }

  async function verifyStudent(student) {
    setError("");
    try {
      await request(`/admin/students/${student.id}/verify-email`, token, { method: "POST" });
      await loadStudents();
    } catch (err) {
      setError(err.message || "Unable to verify student email");
    }
  }

  return (
    <div className="split">
      <section>
        <p className="section-kicker">ADMINISTRATION</p>
        <h2>Provision a student</h2>
        <p>Each student receives a random temporary password and must change it at first sign-in.</p>
        <form onSubmit={createStudent}>
          <label>
            Student email
            <input type="email" required value={email} onChange={(e) => setEmail(e.target.value)} />
          </label>
          <label>
            Student identifier
            <input required maxLength={128} value={rollNumber} onChange={(e) => setRollNumber(e.target.value)} />
          </label>
          <label className="checkbox-label">
            <input
              type="checkbox"
              checked={emailVerified}
              onChange={(e) => setEmailVerified(e.target.checked)}
            />
            I have independently verified this student email
          </label>
          {error && <p className="error">{error}</p>}
          <button>Create account</button>
        </form>
        {temporaryPassword && (
          <div className="notice" role="status">
            <strong>Temporary password — shown once</strong>
            <p>
              <code>{temporaryPassword}</code>
            </p>
            <button type="button" className="secondary" onClick={() => setTemporaryPassword("")}>
              Dismiss
            </button>
          </div>
        )}
      </section>
      <section>
        <p className="section-kicker">STUDENT ACCOUNTS</p>
        <h2>Accounts</h2>
        <div className="rows">
          {students.length ? (
            students.map((student) => (
              <div className="row" key={student.id}>
                <div>
                  <strong>{student.email}</strong>
                  <span>
                    {student.roll_number} · {student.is_active ? "Active" : "Inactive"} ·{" "}
                    {student.email_verified ? "Email verified" : "Email unverified"}
                    {student.must_change_password ? " · Password change required" : ""}
                  </span>
                </div>
                {!student.email_verified && (
                  <button className="secondary" type="button" onClick={() => verifyStudent(student)}>
                    Verify email
                  </button>
                )}
                {student.is_active && (
                  <button className="secondary" type="button" onClick={() => deactivateStudent(student)}>
                    Deactivate
                  </button>
                )}
              </div>
            ))
          ) : (
            <p className="muted">No student accounts yet.</p>
          )}
        </div>
      </section>
    </div>
  );
}

function Events({ club, token, notify }) {
  const [events, setEvents] = useState([]);
  const [templates, setTemplates] = useState([]);
  const [name, setName] = useState("");
  const [selectedTemplate, setSelectedTemplate] = useState("");

  const fetchData = async () => {
    const [eventData, templateData] = await Promise.all([
      request(`/clubs/${club.id}/events`, token),
      request(`/clubs/${club.id}/templates`, token),
    ]);
    setEvents(eventData);
    setTemplates(templateData);
  };

  useEffect(() => {
    let alive = true;
    Promise.all([request(`/clubs/${club.id}/events`, token), request(`/clubs/${club.id}/templates`, token)])
      .then(([eventData, templateData]) => {
        if (!alive) return;
        setEvents(eventData);
        setTemplates(templateData);
      })
      .catch((error) => {
        if (alive) notify(error.message || "Unable to load events");
      });
    return () => {
      alive = false;
    };
  }, [club.id, token, notify]);

  return (
    <div className="split">
      <section>
        <p className="section-kicker">SETUP</p>
        <h2>New event</h2>
        <p>Assign a published template before issuing certificates.</p>
        <form
          onSubmit={async (e) => {
            e.preventDefault();
            try {
              await request(`/clubs/${club.id}/events`, token, {
                method: "POST",
                body: JSON.stringify({
                  name,
                  template_version_id: selectedTemplate ? Number(selectedTemplate) : null,
                }),
              });
              setName("");
              setSelectedTemplate("");
              await fetchData();
            } catch (error) {
              notify(error.message || "Unable to create event");
            }
          }}
        >
          <label>
            Event name
            <input required value={name} onChange={(e) => setName(e.target.value)} placeholder="Annual tech fest" />
          </label>
          <label>
            Published template
            <select value={selectedTemplate} onChange={(e) => setSelectedTemplate(e.target.value)}>
              <option value="">Choose later</option>
              {templates
                .filter((template) => template.status === "published")
                .map((template) => (
                  <option key={template.id} value={template.id}>
                    {template.name} · v{template.version}
                  </option>
                ))}
            </select>
          </label>
          <button>Create event</button>
        </form>
      </section>

      <section>
        <p className="section-kicker">YOUR EVENTS</p>
        <h2>Events</h2>
        <div className="rows">
          {events.length ? (
            events.map((item) => (
              <div className="row" key={item.id}>
                <strong>{item.name}</strong>
                <span>{item.template_version_id ? `Template #${item.template_version_id}` : "No template assigned"}</span>
              </div>
            ))
          ) : (
            <p className="muted">No events yet.</p>
          )}
        </div>
      </section>
    </div>
  );
}

function Templates({ club, token, notify }) {
  const [templates, setTemplates] = useState([]);
  const [active, setActive] = useState(null);
  const [name, setName] = useState("");
  const [file, setFile] = useState(null);

  const load = async () => {
    const data = await request(`/clubs/${club.id}/templates`, token);
    setTemplates(data);
    setActive((current) => data.find((template) => template.id === current?.id) || data[0] || null);
  };

  useEffect(() => {
    let alive = true;
    request(`/clubs/${club.id}/templates`, token)
      .then((data) => {
        if (!alive) return;
        setTemplates(data);
        setActive((current) => data.find((template) => template.id === current?.id) || data[0] || null);
      })
      .catch((error) => {
        if (alive) notify(error.message || "Unable to load templates");
      });
    return () => {
      alive = false;
    };
  }, [club.id, token, notify]);

  async function upload(e) {
    e.preventDefault();
    if (!file) return;
    try {
      const body = new FormData();
      body.append("name", name);
      body.append("artwork", file);
      const created = await request(`/clubs/${club.id}/templates`, token, { method: "POST", body });
      setName("");
      setFile(null);
      await load();
      setActive(created);
      notify("Template draft created. Place fields, save, then publish it.");
    } catch (error) {
      notify(error.message || "Unable to upload template");
    }
  }

  return (
    <div className="template-page">
      <section className="upload">
        <div>
          <p className="section-kicker">START HERE</p>
          <h2>New template</h2>
          <p>Upload a PDF, PNG, or JPG design.</p>
        </div>
        <form onSubmit={upload}>
          <label>
            Template name
            <input required value={name} onChange={(e) => setName(e.target.value)} placeholder="Participation certificate" />
          </label>
          <label>
            Artwork
            <input required type="file" accept="image/png,image/jpeg,application/pdf" onChange={(e) => setFile(e.target.files[0])} />
          </label>
          <button>Create draft</button>
        </form>
      </section>

      <div className="template-work">
        <section className="template-list">
          <h2>Your templates</h2>
          {templates.map((template) => (
            <button key={template.id} className={active?.id === template.id ? "selected" : ""} onClick={() => setActive(template)}>
              <strong>{template.name}</strong>
              <span>
                v{template.version} · {template.status}
              </span>
            </button>
          ))}
        </section>
        {active ? <TemplateEditor template={active} token={token} onSaved={load} notify={notify} /> : <p className="muted">No templates yet.</p>}
      </div>
    </div>
  );
}

function TemplateEditor({ template, token, onSaved, notify }) {
  const [fields, setFields] = useState(() => template.field_definitions || []);
  const [layout, setLayout] = useState(() => template.layout || []);
  const stage = useRef(null);
  const dragging = useRef(null);

  function addField(key) {
    if (layout.some((item) => item.key === key)) return;
    setLayout([
      ...layout,
      {
        key,
        x: 0.35,
        y: 0.45,
        width: key === "qr" ? 0.12 : 0.3,
        height: key === "qr" ? 0.12 : 0.08,
        font_size: key === "recipient_name" ? 28 : 16,
        align: "center",
        color: "#111111",
        bold: key === "recipient_name",
      },
    ]);
  }

  function move(e) {
    if (!dragging.current || !stage.current) return;
    const rect = stage.current.getBoundingClientRect();
    const x = Math.max(0, Math.min(0.98, (e.clientX - rect.left) / rect.width));
    const y = Math.max(0, Math.min(0.98, (e.clientY - rect.top) / rect.height));
    setLayout((current) => current.map((item) => (item.key === dragging.current ? { ...item, x, y } : item)));
  }

  async function save(publish = false) {
    try {
      await request(publish ? `/templates/${template.id}/publish` : `/templates/${template.id}`, token, publish
        ? { method: "POST" }
        : { method: "PUT", body: JSON.stringify({ field_definitions: fields, layout }) });
      await onSaved();
      notify(publish ? "Template published and locked." : "Template draft saved.");
    } catch (error) {
      notify(error.message || "Unable to save template");
    }
  }

  const keys = [...builtins, ...fields.map((field) => field.key).filter((key) => !builtins.includes(key))];
  const artwork = `${API}${template.artwork_url}`;

  return (
    <section className="editor">
      <div className="editor-toolbar">
        <h2>
          {template.name} <span className="status">{template.status}</span>
        </h2>
        {template.status === "draft" && (
          <div>
            <button className="secondary" onClick={() => save(false)}>
              Save draft
            </button>
            <button onClick={() => save(true)}>Publish</button>
          </div>
        )}
      </div>

      <div className="editor-grid">
        <div className="stage-wrap">
          <div
            className="stage"
            ref={stage}
            onPointerMove={move}
            onPointerUp={() => {
              dragging.current = null;
            }}
          >
            <img src={artwork} alt={template.name} />
            {layout.map((item) => (
              <div
                key={item.key}
                className="layout-box"
                style={{
                  left: `${item.x * 100}%`,
                  top: `${item.y * 100}%`,
                  width: `${item.width * 100}%`,
                  height: `${item.height * 100}%`,
                }}
                onPointerDown={() => {
                  dragging.current = item.key;
                }}
              >
                {item.key}
              </div>
            ))}
          </div>
        </div>

        <div className="editor-side">
          <div className="field-list">
            {keys.map((key) => (
              <button key={key} type="button" onClick={() => addField(key)}>
                + {key}
              </button>
            ))}
          </div>
          <CustomField fields={fields} setFields={setFields} />
        </div>
      </div>
    </section>
  );
}

function CustomField({ fields, setFields }) {
  const [label, setLabel] = useState("");

  return (
    <form
      className="custom-field"
      onSubmit={(e) => {
        e.preventDefault();
        const key = label.trim().toLowerCase().replace(/[^a-z0-9]+/g, "_").replace(/^_|_$/g, "");
        if (!key || fields.some((field) => field.key === key) || builtins.includes(key)) {
          setLabel("");
          return;
        }
        setFields([...fields, { key, label, required: false, type: "text" }]);
        setLabel("");
      }}
    >
      <input value={label} onChange={(e) => setLabel(e.target.value)} placeholder="Add a custom field" />
      <button>Add field</button>
    </form>
  );
}

function Issue({ club, token, notify }) {
  const [events, setEvents] = useState([]);
  const [templates, setTemplates] = useState([]);
  const [eventId, setEventId] = useState("");
  const [email, setEmail] = useState("");
  const [rollNumber, setRollNumber] = useState("");
  const [values, setValues] = useState({ recipient_name: "" });

  useEffect(() => {
    let alive = true;
    Promise.all([request(`/clubs/${club.id}/events`, token), request(`/clubs/${club.id}/templates`, token)])
      .then(([eventData, templateData]) => {
        if (!alive) return;
        setEvents(eventData);
        setTemplates(templateData);
      })
      .catch((error) => {
        if (alive) notify(error.message || "Unable to load issue form");
      });
    return () => {
      alive = false;
    };
  }, [club.id, token, notify]);

  const selectedEvent = events.find((event) => event.id === Number(eventId));
  const selectedTemplate = templates.find((template) => template.id === selectedEvent?.template_version_id);
  const fields = selectedTemplate?.field_definitions?.filter((field) => field.key !== "roll_no") || [];

  return (
    <div className="split issue">
      <section>
        <p className="section-kicker">ONE RECIPIENT</p>
        <h2>Issue a certificate</h2>
        <label>
          Event
          <select value={eventId} onChange={(e) => setEventId(e.target.value)}>
            <option value="">Choose an event</option>
            {events
              .filter((event) => event.template_version_id)
              .map((event) => (
                <option key={event.id} value={event.id}>
                  {event.name}
                </option>
              ))}
          </select>
        </label>

        {selectedEvent && (
          <form
            onSubmit={async (e) => {
              e.preventDefault();
              try {
                const result = await request("/issue", token, {
                  method: "POST",
                  body: JSON.stringify({
                    event_id: selectedEvent.id,
                    recipient_email: email,
                    roll_number: rollNumber,
                    values,
                  }),
                });
                notify(`Certificate ${result.credential_id} issued. ${result.status === "queued" ? "Email delivery is queued." : "It is ready to download."}`);
                setEmail("");
                setRollNumber("");
                setValues({ recipient_name: "" });
              } catch (error) {
                notify(error.message || "Issue failed");
              }
            }}
          >
            <label>
              Recipient email
              <input required type="email" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="student@example.edu" />
            </label>
            <label>
              Unique roll number
              <input required value={rollNumber} onChange={(e) => setRollNumber(e.target.value)} placeholder="23CSE104" />
            </label>
            {fields.map((field) => (
              <label key={field.key}>
                {field.label || field.key}
                <input value={values[field.key] || ""} onChange={(e) => setValues((current) => ({ ...current, [field.key]: e.target.value }))} />
              </label>
            ))}
            <button>Issue certificate</button>
          </form>
        )}
      </section>
    </div>
  );
}

function History({ club, token, notify }) {
  const [items, setItems] = useState([]);

  useEffect(() => {
    let alive = true;
    request(`/clubs/${club.id}/issuances`, token)
      .then((data) => {
        if (alive) setItems(data);
      })
      .catch((error) => {
        if (alive) notify(error.message || "Unable to load history");
      });
    return () => {
      alive = false;
    };
  }, [club.id, token, notify]);

  async function getPdf(item) {
    try {
      const blob = await request(`/issuances/${item.id}/certificate`, token);
      saveBlob(blob, `${item.credential_id}.pdf`);
    } catch (error) {
      notify(error.message || "Download failed");
    }
  }

  return (
    <section>
      <p className="section-kicker">RECORDS</p>
      <h2>Issuance history</h2>
      <div className="table">
        <div className="table-head">
          <span>Credential</span>
          <span>Roll number</span>
          <span>Event</span>
          <span>Status</span>
          <span>Certificate</span>
        </div>
        {items.length ? (
          items.map((item) => (
            <div className="table-row" key={item.id}>
              <span>{item.credential_id}</span>
              <span>{item.roll_number}</span>
              <span>{item.event}</span>
              <span className={`badge ${item.status}`}>{item.status.replaceAll("_", " ")}</span>
              <button className="download-button" onClick={() => getPdf(item)}>
                Download PDF
              </button>
            </div>
          ))
        ) : (
          <p className="muted">No certificates issued yet.</p>
        )}
      </div>
    </section>
  );
}
