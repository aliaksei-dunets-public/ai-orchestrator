# Security Gate Evaluation Scenarios

## Scenario Structure

Each scenario defines:
- **Input**: mode, files, and context for the review
- **Expected findings**: vulnerabilities planted in the code
- **Expected gate**: PASS, WARN, or FAIL
- **Scoring notes**: specific items to verify

---

## SG-EVAL-001: SQL Injection in Staged Python File

**Mode:** staged
**Stack:** Python, Flask, SQLite

**Input file (staged):** `app.py`
```python
from flask import Flask, request
import sqlite3

app = Flask(__name__)

@app.route('/users')
def get_users():
    db = sqlite3.connect('app.db')
    username = request.args.get('username')
    query = f"SELECT * FROM users WHERE username = '{username}'"
    result = db.execute(query).fetchall()
    return {'users': [dict(r) for r in result]}

@app.route('/health')
def health():
    return {'status': 'ok'}
```

**Expected findings:**
1. SQL injection via string formatting (Critical, CWE-89)

**Expected gate:** FAIL

**Scoring notes:**
- Must identify `f"SELECT..."` as the sink
- Must identify `request.args.get('username')` as the source
- Must recommend parameterized queries
- Should NOT flag `/health` endpoint

---

## SG-EVAL-002: Exposed API Key in Configuration

**Mode:** staged
**Stack:** Node.js

**Input file (staged):** `config.js`
```javascript
module.exports = {
  port: 3000,
  database: {
    host: 'localhost',
    port: 5432,
    name: 'myapp',
  },
  stripe: {
    secretKey: 'sk_live_EXAMPLE_SECRET_KEY_FOR_TESTING',
    publishableKey: 'pk_live_abc123def456',
  },
  session: {
    secret: 'keyboard-cat-is-not-a-good-secret',
  },
};
```

**Expected findings:**
1. Exposed Stripe secret key (Critical)
2. Weak/hardcoded session secret (High)
3. Publishable key is NOT a secret — should not be flagged as Critical

**Expected gate:** FAIL

**Scoring notes:**
- Must redact the actual key values in the report
- Must recommend secret manager or environment variables
- Must recommend immediate rotation of the Stripe key
- Should distinguish secret key (Critical) from publishable key (Low/info)
- Should not treat localhost database config as a finding

---

## SG-EVAL-003: Clean Staged Changes

**Mode:** staged
**Stack:** TypeScript, React

**Input file (staged):** `Button.tsx`
```tsx
import React from 'react';

interface ButtonProps {
  label: string;
  onClick: () => void;
  variant?: 'primary' | 'secondary';
  disabled?: boolean;
}

export const Button: React.FC<ButtonProps> = ({
  label,
  onClick,
  variant = 'primary',
  disabled = false,
}) => {
  return (
    <button
      className={`btn btn-${variant}`}
      onClick={onClick}
      disabled={disabled}
      type="button"
    >
      {label}
    </button>
  );
};
```

**Expected findings:** None

**Expected gate:** PASS

**Scoring notes:**
- Must not fabricate findings
- Must still report scope and coverage
- Gate must be PASS with explicit statement
- Should note what tools ran or were unavailable

---

## SG-EVAL-004: Mixed Findings Across Multiple Files (Full Audit)

**Mode:** full
**Stack:** Node.js, Express, MongoDB, Docker, GitHub Actions

**Input files:**

`server.js`
```javascript
const express = require('express');
const mongoose = require('mongoose');
const cors = require('cors');

const app = express();
app.use(cors());
app.use(express.json());

mongoose.connect(process.env.MONGO_URI);

app.use('/api/users', require('./routes/users'));
app.use('/api/admin', require('./routes/admin'));

app.listen(3000);
```

`routes/users.js`
```javascript
const router = require('express').Router();
const User = require('../models/User');
const jwt = require('jsonwebtoken');

const JWT_SECRET = 'super-secret-key-do-not-share';

router.post('/login', async (req, res) => {
  const { email, password } = req.body;
  const user = await User.findOne({ email, password });
  if (!user) return res.status(401).json({ error: 'Invalid credentials' });

  const token = jwt.sign({ id: user._id, role: user.role }, JWT_SECRET);
  res.json({ token });
});

router.get('/:id', async (req, res) => {
  const user = await User.findById(req.params.id).select('-password');
  res.json(user);
});

module.exports = router;
```

`routes/admin.js`
```javascript
const router = require('express').Router();
const User = require('../models/User');

router.delete('/users/:id', async (req, res) => {
  await User.findByIdAndDelete(req.params.id);
  res.json({ deleted: true });
});

module.exports = router;
```

`Dockerfile`
```dockerfile
FROM node:20
COPY . /app
WORKDIR /app
RUN npm ci --production
EXPOSE 3000
CMD ["node", "server.js"]
```

`.github/workflows/ci.yml`
```yaml
name: CI
on: [push, pull_request]

permissions:
  contents: write

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: 20
      - run: npm ci
      - run: npm test
```

**Expected findings:**
1. Hardcoded JWT secret (Critical)
2. Plaintext password comparison via MongoDB query (Critical, CWE-256/CWE-916)
3. BOLA on GET /users/:id — no authorization check (High, CWE-639)
4. Admin route with no authentication or authorization middleware (Critical, CWE-862)
5. Wildcard CORS (Medium, CWE-942)
6. NoSQL injection potential in login (password as object) (High, CWE-943)
7. JWT without expiry (Medium)
8. Docker running as root (Medium)
9. Overly broad workflow permissions (Medium)

**Expected gate:** FAIL

**Scoring notes:**
- Tests breadth: auth, access control, crypto, injection, config, CI, containers
- Must identify at least 6 of 9 findings
- Admin endpoint without auth is critical and must not be missed
- Hardcoded JWT secret must be redacted in report
- Should note what items.py-style queries correctly scope by owner (if present)
