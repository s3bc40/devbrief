use ignore::Walk;
use pyo3::prelude::*;
use regex::Regex;
use std::collections::HashSet;
use std::fs;
use std::io::Read;

// ---------------------------------------------------------------------------
// Types — pub so the pymodule can re-export them via #[pymodule_export]
// ---------------------------------------------------------------------------

#[pyclass]
pub struct EnvDiff {
    #[pyo3(get)]
    pub missing_from_env: Vec<String>,
    #[pyo3(get)]
    pub undocumented_in_example: Vec<String>,
}

#[pyclass]
pub struct SecretMatch {
    #[pyo3(get)]
    pub file: String,
    #[pyo3(get)]
    pub line: usize,
    #[pyo3(get)]
    pub pattern_name: String,
    #[pyo3(get)]
    pub masked_value: String,
}

// ---------------------------------------------------------------------------
// Pure Rust helpers — pub(crate) so the #[cfg(test)] module can call them
// ---------------------------------------------------------------------------

pub(crate) fn parse_env_keys(content: &str) -> HashSet<String> {
    content
        .lines()
        .map(|l| l.trim())
        .filter(|l| !l.is_empty() && !l.starts_with('#'))
        .filter_map(|l| l.split('=').next())
        .map(|k| k.trim().to_string())
        .filter(|k| !k.is_empty())
        .collect()
}

pub(crate) fn diff_env_files_impl(env_path: &str, example_path: &str) -> EnvDiff {
    let env_keys = match fs::read_to_string(env_path) {
        Ok(c) => parse_env_keys(&c),
        Err(_) => {
            return EnvDiff {
                missing_from_env: vec![],
                undocumented_in_example: vec![],
            }
        }
    };
    let example_keys = match fs::read_to_string(example_path) {
        Ok(c) => parse_env_keys(&c),
        Err(_) => {
            return EnvDiff {
                missing_from_env: vec![],
                undocumented_in_example: vec![],
            }
        }
    };

    let mut missing: Vec<String> = example_keys.difference(&env_keys).cloned().collect();
    let mut undocumented: Vec<String> = env_keys.difference(&example_keys).cloned().collect();
    missing.sort();
    undocumented.sort();

    EnvDiff {
        missing_from_env: missing,
        undocumented_in_example: undocumented,
    }
}

const SECRET_PATTERNS: &[(&str, &str)] = &[
    ("anthropic_api_key", r"sk-ant-[a-zA-Z0-9]{32,}"),
    ("openai_api_key", r"sk-[a-zA-Z0-9]{48,}"),
    ("aws_access_key_id", r"AKIA[0-9A-Z]{16}"),
    ("github_token", r"(ghp_|gho_|ghu_|ghs_)[a-zA-Z0-9]{36,}"),
    (
        "private_key_header",
        r"-----BEGIN (RSA|EC|OPENSSH) PRIVATE KEY-----",
    ),
];

pub(crate) fn scan_secrets_impl(path: &str) -> Vec<SecretMatch> {
    let compiled: Vec<(&str, Regex)> = SECRET_PATTERNS
        .iter()
        .map(|(name, pat)| (*name, Regex::new(pat).expect("invalid pattern")))
        .collect();

    let mut results = Vec::new();

    for entry in Walk::new(path) {
        let entry = match entry {
            Ok(e) => e,
            Err(_) => continue,
        };

        let file_path = entry.path();
        if !file_path.is_file() {
            continue;
        }

        let path_str = file_path.to_string_lossy().to_string();

        // Skip rust/target/ unconditionally regardless of .gitignore
        if path_str.contains("rust/target") || path_str.contains("rust\\target") {
            continue;
        }

        // Read file bytes
        let mut file = match fs::File::open(file_path) {
            Ok(f) => f,
            Err(_) => continue,
        };
        let mut buf = Vec::new();
        if file.read_to_end(&mut buf).is_err() {
            continue;
        }

        // Skip binary files: check first 512 bytes for null bytes
        if buf[..buf.len().min(512)].contains(&0) {
            continue;
        }

        // Skip non-UTF-8 files
        let content = match String::from_utf8(buf) {
            Ok(s) => s,
            Err(_) => continue,
        };

        for (line_idx, line) in content.lines().enumerate() {
            for (pattern_name, regex) in &compiled {
                if let Some(mat) = regex.find(line) {
                    let matched = mat.as_str();
                    let masked = if matched.len() >= 4 {
                        format!("{}***", &matched[..4])
                    } else {
                        "***".to_string()
                    };
                    results.push(SecretMatch {
                        file: path_str.clone(),
                        line: line_idx + 1,
                        pattern_name: pattern_name.to_string(),
                        masked_value: masked,
                    });
                }
            }
        }
    }

    results
}

// ---------------------------------------------------------------------------
// PyO3 module — thin wrappers; all logic lives in the pub(crate) functions
// ---------------------------------------------------------------------------

#[pymodule]
mod _devbrief_core {
    use pyo3::prelude::*;

    #[pymodule_export]
    use super::EnvDiff;
    #[pymodule_export]
    use super::SecretMatch;

    /// Compare .env and .env.example key sets.
    /// Returns an empty diff (not an error) when either file is absent.
    #[pyfunction]
    fn diff_env_files(env_path: &str, example_path: &str) -> super::EnvDiff {
        super::diff_env_files_impl(env_path, example_path)
    }

    /// Walk `path` recursively (respecting .gitignore) and return secret matches.
    #[pyfunction]
    fn scan_secrets(path: &str) -> Vec<super::SecretMatch> {
        super::scan_secrets_impl(path)
    }
}

// ---------------------------------------------------------------------------
// Rust unit tests
// ---------------------------------------------------------------------------

#[cfg(test)]
mod tests {
    use super::*;
    use std::fs;
    use tempfile::tempdir;

    // ── parse_env_keys ────────────────────────────────────────────────────

    #[test]
    fn test_parse_env_keys_empty_input() {
        assert!(parse_env_keys("").is_empty());
    }

    #[test]
    fn test_parse_env_keys_skips_comment_lines() {
        let keys = parse_env_keys("# comment=yes\nAPI_KEY=abc\n");
        assert!(!keys.contains("# comment=yes"));
        assert!(keys.contains("API_KEY"));
        assert_eq!(keys.len(), 1);
    }

    #[test]
    fn test_parse_env_keys_skips_blank_lines() {
        let keys = parse_env_keys("\n\nDB_URL=postgres\n\n");
        assert!(keys.contains("DB_URL"));
        assert_eq!(keys.len(), 1);
    }

    #[test]
    fn test_parse_env_keys_trims_key_whitespace() {
        // "  MY_KEY  = value  " → key should be "MY_KEY"
        let keys = parse_env_keys("  MY_KEY  = value  \n");
        assert!(keys.contains("MY_KEY"), "got: {:?}", keys);
        assert_eq!(keys.len(), 1);
    }

    #[test]
    fn test_parse_env_keys_deduplicates() {
        // HashSet: repeated key counts once
        let keys = parse_env_keys("DUPE=first\nDUPE=second\n");
        assert!(keys.contains("DUPE"));
        assert_eq!(keys.len(), 1);
    }

    // ── diff_env_files_impl ───────────────────────────────────────────────

    #[test]
    fn test_diff_key_missing_from_env() {
        let dir = tempdir().unwrap();
        let env = dir.path().join(".env");
        let example = dir.path().join(".env.example");
        fs::write(&env, "API_KEY=abc\n").unwrap();
        fs::write(&example, "API_KEY=\nDB_URL=\n").unwrap();

        let result = diff_env_files_impl(env.to_str().unwrap(), example.to_str().unwrap());

        assert!(result.missing_from_env.contains(&"DB_URL".to_string()));
        assert!(result.undocumented_in_example.is_empty());
    }

    #[test]
    fn test_diff_undocumented_key_in_example() {
        let dir = tempdir().unwrap();
        let env = dir.path().join(".env");
        let example = dir.path().join(".env.example");
        fs::write(&env, "API_KEY=abc\nSECRET_VAR=xyz\n").unwrap();
        fs::write(&example, "API_KEY=\n").unwrap();

        let result = diff_env_files_impl(env.to_str().unwrap(), example.to_str().unwrap());

        assert!(result.undocumented_in_example.contains(&"SECRET_VAR".to_string()));
        assert!(result.missing_from_env.is_empty());
    }

    #[test]
    fn test_diff_clean_state_returns_empty() {
        let dir = tempdir().unwrap();
        let env = dir.path().join(".env");
        let example = dir.path().join(".env.example");
        fs::write(&env, "API_KEY=abc\nDB_URL=postgres\n").unwrap();
        fs::write(&example, "API_KEY=\nDB_URL=\n").unwrap();

        let result = diff_env_files_impl(env.to_str().unwrap(), example.to_str().unwrap());

        assert!(result.missing_from_env.is_empty());
        assert!(result.undocumented_in_example.is_empty());
    }

    // ── scan_secrets_impl ─────────────────────────────────────────────────

    #[test]
    fn test_scan_aws_access_key_matches() {
        let dir = tempdir().unwrap();
        // AKIA + 16 uppercase/digit chars = valid aws_access_key_id
        fs::write(
            dir.path().join("config.py"),
            "AWS_ACCESS_KEY_ID = \"AKIAIOSFODNN7EXAMPLE\"\n",
        )
        .unwrap();

        let results = scan_secrets_impl(dir.path().to_str().unwrap());

        assert_eq!(results.len(), 1);
        assert_eq!(results[0].pattern_name, "aws_access_key_id");
        assert_eq!(results[0].masked_value, "AKIA***");
        assert_eq!(results[0].line, 1);
    }

    #[test]
    fn test_scan_anthropic_key_matches() {
        let dir = tempdir().unwrap();
        // sk-ant- + 32 alphanumeric chars
        fs::write(
            dir.path().join("secrets.txt"),
            "ANTHROPIC_API_KEY=sk-ant-abcdefghijklmnopqrstuvwxyz123456\n",
        )
        .unwrap();

        let results = scan_secrets_impl(dir.path().to_str().unwrap());

        assert_eq!(results.len(), 1);
        assert_eq!(results[0].pattern_name, "anthropic_api_key");
        assert_eq!(results[0].masked_value, "sk-a***");
    }

    #[test]
    fn test_scan_private_key_header_matches() {
        let dir = tempdir().unwrap();
        fs::write(
            dir.path().join("id_rsa"),
            "-----BEGIN RSA PRIVATE KEY-----\nMIIEowIBAAKCAQ\n",
        )
        .unwrap();

        let results = scan_secrets_impl(dir.path().to_str().unwrap());

        assert_eq!(results.len(), 1);
        assert_eq!(results[0].pattern_name, "private_key_header");
        assert_eq!(results[0].masked_value, "----***");
    }

    #[test]
    fn test_scan_clean_file_no_match() {
        let dir = tempdir().unwrap();
        fs::write(
            dir.path().join("main.py"),
            "# No secrets here\nprint('hello world')\n",
        )
        .unwrap();

        let results = scan_secrets_impl(dir.path().to_str().unwrap());

        assert!(results.is_empty());
    }
}
