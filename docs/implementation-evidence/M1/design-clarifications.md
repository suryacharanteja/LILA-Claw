# M1 review decisions pending

## Bootstrap launch arguments

LLD-06 directs the trusted launcher to open an HTTPS URL containing a 32-byte,
single-use, 60-second bootstrap capability in the fragment. LLD-01 also prohibits
secrets in command-line arguments. Standard Windows browser activation can place
the URL in browser process arguments. Both requirements cannot be guaranteed by
the current OS browser-launch path.

Owner decision requested: permit a narrow exception for the short-lived bootstrap
fragment during OS browser activation, or require an alternative such as manual
bootstrap entry. No exception applies to worker/provider credentials or renewable
session secrets. Until resolved, automatic authenticated UI launch is disabled;
the runtime and test-only in-process/isolated-browser qualification remain usable.

No change to the approved baselines has been recorded as approved. The optional
configuration flag allow_fragment_launch defaults to false and is not exposed by
the setup flow. It must not be enabled before the owner decision is recorded.

## Temporary Chrome certificate qualification

LLD-06 explicitly requires setup confirmation before adding the installation CA
to CurrentUser Root. The prepared qualification certificate is:

- Installation: 36b6c93c-b9fd-41f4-a2db-b1084653f6ad
- SHA-1 certificate thumbprint: D46EEBF7C0B8CF5176B7CD7B3C5E3F840006E164
- Constraints: localhost, 127.0.0.1/32, ::1/128; path length zero
- Chrome available: 152.0.7977.76

The qualification script uses a separate Chrome profile and test-only CDP, not
the production browser controller. It passes no bootstrap secret in argv, uses
no certificate-validation bypass, and removes only its newly added certificate
in finally cleanup. A pre-existing matching certificate causes the test to refuse
the change. Authorization is pending; the script has not changed the trust store.

## Auth-store implementation additions

M1 adds version 2 of the auth schema: auth_command_receipts for idempotent
revocation, plus auth_schema_migrations for checksummed migration history. This
implements the approved command-id and migration contracts without changing
business behavior. Receipts contain no bootstrap/session/CSRF secrets. These
tables remain inside the separate encrypted auth store and excluded from
business backup. The approved version-1 SQL artifacts remain byte-for-byte intact.

## Decision update

The owner delegated these technical decisions; both were approved within their disclosed scope. See [decision record](../../approval-records/M1-trust-and-bootstrap-decision.md). Chrome qualification passed with normal certificate validation. The temporary CA removal remains pending: Windows returned ERROR_CANCELLED, and automatic approval review blocked the follow-up removal command with no more specific reason. Automatic launch is enabled for newly prepared installations under the narrow exception. Earlier pending-decision text above is historical.
