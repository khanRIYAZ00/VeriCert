import { useState } from "react";
import "./App.css";

const API = "http://127.0.0.1:8000";

function App() {
  const [page, setPage] = useState("home");

  return (
    <div className="app">
      <header>
        <h1>VeriCert</h1>
        <p>Digital Academic Credential Verification</p>
      </header>

      <nav>
        <button onClick={() => setPage("home")}>
          Home
        </button>

        <button onClick={() => setPage("issue")}>
          Issue Certificate
        </button>

        <button onClick={() => setPage("verify")}>
          Verify Certificate
        </button>
      </nav>

      <main>
        {page === "home" && <Home />}
        {page === "issue" && <IssueCertificate />}
        {page === "verify" && <VerifyCertificate />}
      </main>
    </div>
  );
}

function Home() {
  return (
    <section>
      <h2>Cryptographically Verifiable Credentials</h2>

      <p>
        VeriCert allows institutions to issue digitally
        signed academic credentials that can be independently
        verified.
      </p>

      <div className="cards">
        <div>
          <h3>Digital Signature</h3>
          <p>Ed25519 institutional signing.</p>
        </div>

        <div>
          <h3>Integrity</h3>
          <p>SHA-256 credential hashing.</p>
        </div>

        <div>
          <h3>QR Verification</h3>
          <p>Portable signed credential.</p>
        </div>
      </div>
    </section>
  );
}


function IssueCertificate() {
  const [form, setForm] = useState({
    name: "",
    qualification: "",
    graduation_year: 2026,
    cgpa: 0,
  });

  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);

  function update(field, value) {
    setForm({
      ...form,
      [field]: value,
    });
  }

  async function issue() {
    setLoading(true);
    setResult(null);

    try {
      const response = await fetch(`${API}/issue`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          ...form,
          graduation_year: Number(form.graduation_year),
          cgpa: Number(form.cgpa),
        }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "Issuance failed");
      }

      setResult(data);
    } catch (error) {
      alert(error.message);
    }

    setLoading(false);
  }

  return (
    <section>
      <h2>Issue Certificate</h2>

      <div className="form">
        <label>
          Student Name

          <input
            value={form.name}
            onChange={(e) =>
              update("name", e.target.value)
            }
          />
        </label>

        <label>
          Qualification

          <input
            value={form.qualification}
            onChange={(e) =>
              update("qualification", e.target.value)
            }
          />
        </label>

        <label>
          Graduation Year

          <input
            type="number"
            value={form.graduation_year}
            onChange={(e) =>
              update("graduation_year", e.target.value)
            }
          />
        </label>

        <label>
          CGPA

          <input
            type="number"
            step="0.1"
            min="0"
            max="10"
            value={form.cgpa}
            onChange={(e) =>
              update("cgpa", e.target.value)
            }
          />
        </label>

        <button onClick={issue} disabled={loading}>
          {loading ? "Generating..." : "Generate Certificate"}
        </button>
      </div>

      {result && (
        <div className="result">
          <h3>Certificate Generated</h3>

          <p>
            <strong>ID:</strong>{" "}
            {result.credential.credential_id}
          </p>

          <p>
            <strong>SHA-256:</strong>
            <br />
            <code>{result.hash}</code>
          </p>

          <p>
            <strong>Signature:</strong> Ed25519
          </p>

          <p>
            <strong>QR:</strong> {result.qr_file}
          </p>

          <p>
            <strong>PDF:</strong> {result.certificate_file}
          </p>

          <pre>
            {JSON.stringify(result.credential, null, 2)}
          </pre>
        </div>
      )}
    </section>
  );
}


function VerifyCertificate() {
  const [input, setInput] = useState("");
  const [result, setResult] = useState(null);

  async function verify() {
    try {
      const packageData = JSON.parse(input);

      const response = await fetch(`${API}/verify-qr`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(packageData),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "Verification failed");
      }

      setResult(data);
    } catch (error) {
      alert(
        error.message ||
        "Invalid credential JSON"
      );
    }
  }

  return (
    <section>
      <h2>Verify Certificate</h2>

      <p>
        Paste the credential contained in the QR code.
      </p>

      <textarea
        value={input}
        onChange={(e) =>
          setInput(e.target.value)
        }
        placeholder="Paste VeriCert QR credential here..."
      />

      <button onClick={verify}>
        Verify Credential
      </button>

      {result && (
        <div
          className={
            result.verified
              ? "verification valid"
              : "verification invalid"
          }
        >
          <h2>
            {result.verified
              ? "✓ VERIFIED"
              : "✗ INVALID"}
          </h2>

          <p>
            Credential ID:{" "}
            {result.credential.credential_id}
          </p>

          <hr />

          <p>
            Credential format: ✓
          </p>

          <p>
            SHA-256 integrity:{" "}
            {result.checks.hash_valid ? "✓" : "✗"}
          </p>

          <p>
            Digital signature:{" "}
            {result.checks.signature_valid ? "✓" : "✗"}
          </p>
        </div>
      )}
    </section>
  );
}

export default App;