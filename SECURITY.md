# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 0.1.x   | :white_check_mark: |

## Security Considerations

### Google Sheets Sharing

> [!WARNING]
> When using Google Sheets URLs with `--csv-file`, be aware that sharing a sheet with "Anyone with the link" makes it **publicly accessible**. Anyone with the URL can view the data.

**Recommendations**:
- Do **not** include sensitive information in shared Google Sheets (player addresses, phone numbers, etc.)
- Use local CSV files for private or sensitive data
- Regularly review sharing permissions on your Google Sheets
- Consider using a dedicated Google account for sports data

### Video File Processing

> [!CAUTION]
> Processing video files from untrusted sources may pose security risks.

**Best Practices**:
- Only process video files from trusted sources
- Be cautious when processing videos downloaded from the internet
- FFmpeg vulnerabilities could potentially be exploited through malicious video files
- Keep FFmpeg updated to the latest version

### CSV File Parsing

The tool uses `pandas` to parse CSV files, which is generally safe. However:

- Validate CSV files from untrusted sources before processing
- Be aware that malicious CSV files could contain unexpected data
- The tool does not execute any code from CSV files

### Command Injection

The tool constructs FFmpeg commands using user-provided file paths. To prevent command injection:

- File paths are passed as arguments, not shell commands
- The tool uses `subprocess.run()` with list arguments (not shell=True)
- Special characters in filenames are handled safely

**Still, be cautious**:
- Avoid processing files with unusual or suspicious names
- Validate file paths before processing

## Reporting a Vulnerability

If you discover a security vulnerability in Highlight Cuts, please report it responsibly:

### How to Report

1. **Do NOT open a public GitHub issue** for security vulnerabilities
2. Email the maintainer directly at: [your-email@example.com]
3. Include:
   - Description of the vulnerability
   - Steps to reproduce
   - Potential impact
   - Suggested fix (if any)

### What to Expect

- **Acknowledgment**: Within 48 hours
- **Initial Assessment**: Within 1 week
- **Fix Timeline**: Depends on severity
  - Critical: 1-7 days
  - High: 1-2 weeks
  - Medium: 2-4 weeks
  - Low: Best effort

### Disclosure Policy

- We will work with you to understand and address the issue
- We request that you do not publicly disclose the vulnerability until we have released a fix
- We will credit you in the release notes (unless you prefer to remain anonymous)

## Security Best Practices for Users

### 1. Keep Dependencies Updated

```bash
# Update dependencies regularly
uv sync --upgrade
```

### 2. Verify FFmpeg Installation

```bash
# Check FFmpeg version
ffmpeg -version

# Update FFmpeg using your package manager
# macOS:
brew upgrade ffmpeg

# Ubuntu/Debian:
sudo apt update && sudo apt upgrade ffmpeg
```

### 3. Use Virtual Environments

Always use a virtual environment to isolate dependencies:

```bash
# uv automatically creates and manages virtual environments
uv sync
```

### 4. Validate Input Files

Before processing:
- Verify video files are from trusted sources
- Check CSV files for unexpected content
- Use `--dry-run` to preview operations before execution

### 5. Limit Permissions

- Run the tool with minimal necessary permissions
- Avoid running as root/administrator
- Use dedicated directories for output files

## Known Limitations

### Stream Copying Security

The tool uses FFmpeg's `-c copy` mode, which:
- Does not re-encode video (preserves original quality)
- Also preserves any metadata or embedded content in the source video
- If the source video contains malicious metadata, it will be copied to output files

**Mitigation**: Only process videos from trusted sources.

### Google Sheets API

The tool uses the public Google Sheets CSV export endpoint:
- No authentication required for public sheets
- Limited rate limiting (Google may throttle excessive requests)
- No personal data is sent to Google beyond the sheet URL

## Third-Party Dependencies

This project relies on:

- **FFmpeg**: External binary (not managed by Python)
- **pandas**: CSV parsing and data manipulation
- **click**: CLI framework
- **requests**: HTTP library for Google Sheets

**Security Responsibility**:
- We monitor security advisories for Python dependencies
- FFmpeg security is the user's responsibility (keep it updated)
- Use `uv` to ensure reproducible dependency versions

## Security Updates

Security updates will be:
- Released as patch versions (e.g., 0.1.1)
- Announced in release notes
- Tagged with `[SECURITY]` in the changelog

Subscribe to repository releases to stay informed.

---

**Last Updated**: 2025-11-23
