# Contributing to Sungrow SG5.0RS Price-Aware Curtailment

Thank you for your interest in contributing! This project benefits from community contributions.

## How to Contribute

### Reporting Bugs

**Before submitting a bug report:**
- Check existing [Issues](https://github.com/Artic0din/sungrow-sg5-price-curtailment/issues) for duplicates
- Verify the issue is with this integration, not Home Assistant itself
- Test with latest version of this integration

**When submitting a bug report, include:**
- Home Assistant version (`Settings → System → About`)
- Sungrow inverter model (e.g., SG5.0RS)
- WiNet-S firmware version (if known)
- Battery integration used (Teslemetry, etc.)
- Pricing integration used (Amber, etc.)
- Error logs from `Settings → System → Logs`
- Configuration (with secrets redacted)
- Steps to reproduce

**Template:**
```markdown
## Bug Description
Brief description of the issue

## Environment
- Home Assistant: 2024.x.x
- Integration Version: x.x.x
- Inverter Model: SG5.0RS
- Battery: Tesla Powerwall (Teslemetry)
- Pricing: Amber Electric

## Steps to Reproduce
1. Step one
2. Step two
3. Expected vs actual behavior

## Logs
```
Paste relevant error logs here
```

## Configuration
```yaml
# Paste relevant config (redact secrets!)
```
```

### Suggesting Features

**Feature requests should include:**
- Clear use case and problem it solves
- Proposed implementation (if known)
- Compatibility considerations
- Any breaking changes

**Examples of good feature requests:**
- Support for additional inverter models (specify which)
- Integration with other battery systems
- Enhanced price prediction algorithms
- Multi-inverter support

### Pull Requests

**Before submitting a PR:**
1. Open an issue to discuss major changes
2. Test your changes thoroughly
3. Update documentation as needed
4. Follow code style guidelines

**PR Requirements:**
- Clear description of changes
- Link to related issue (if applicable)
- Testing performed
- Documentation updated
- No merge conflicts

**PR Template:**
```markdown
## Description
What does this PR do?

## Related Issue
Fixes #123

## Testing
How was this tested?

## Breaking Changes
List any breaking changes

## Checklist
- [ ] Code tested locally
- [ ] Documentation updated
- [ ] CHANGELOG.md updated
- [ ] No secrets committed
```

## Development Setup

### 1. Fork and Clone

```bash
git clone https://github.com/Artic0din/sungrow-sg5-price-curtailment.git
cd sungrow-sg5-price-curtailment
```

### 2. Create Feature Branch

For issue-backed work, include the issue number in the branch name:

```bash
git checkout -b feat/123-your-feature-name
```

### 3. Make Changes

Edit files in your fork:
- `/config/` - YAML configurations
- `/docs/` - Documentation
- `/examples/` - Example files

### 4. Test Changes

**Install in test Home Assistant instance:**
```bash
# Copy to test HA instance
cp config/packages/sungrow_control.yaml /test-config/packages/
cp config/integrations/modbus_sungrow.yaml /test-config/integrations/

# Restart and verify
ha core check
ha core restart
```

**Test checklist:**
- [ ] Configuration validates (`ha core check`)
- [ ] All sensors appear and have values
- [ ] Automations execute correctly
- [ ] No errors in logs
- [ ] Template sensors work
- [ ] Manual control works
- [ ] Automatic curtailment triggers correctly

### 5. Commit Changes

```bash
git add .
git commit -m "feat: add support for SG6.0RS model"
```

**Commit message format:**
- `feat:` - New feature
- `fix:` - Bug fix
- `docs:` - Documentation only
- `refactor:` - Code restructuring
- `test:` - Testing changes
- `chore:` - Maintenance

### 6. Push and Create PR

```bash
git push origin feat/123-your-feature-name
```

Then create PR on GitHub.

## Code Style

### YAML Guidelines

**Indentation:**
- Use 2 spaces (not tabs)
- Consistent nesting levels

**Naming:**
- Descriptive entity names
- Use snake_case for entity_ids
- Prefix custom sensors with project name

**Comments:**
- Explain non-obvious logic
- Document register addresses
- Include units and ranges

**Example:**
```yaml
# Good
- name: Inverter Total DC Power
  unique_id: inverter_total_dc_power
  address: 5016  # Register 5017-5018
  data_type: uint32
  swap: word
  unit_of_measurement: W
  device_class: power
  state_class: measurement
  scale: 1
  scan_interval: 5  # Real-time monitoring

# Bad
- name: power
  address: 5016
  data_type: uint32
  swap: word
```

### Documentation Guidelines

**Markdown standards:**
- Use proper heading hierarchy (# ## ###)
- Include code blocks with syntax highlighting
- Add tables for structured data
- Link to related documents

**Content requirements:**
- Clear and concise
- Include examples
- Target beginner-friendly explanations
- Keep technical accuracy

## Testing

### Manual Testing Checklist

Before submitting PR, verify:

**Installation:**
- [ ] Fresh install works from README instructions
- [ ] Upgrade from previous version works
- [ ] Rollback procedure works

**Functionality:**
- [ ] All sensors have valid values
- [ ] Manual control works (shutdown/enable)
- [ ] Automations trigger correctly
- [ ] Templates calculate correctly
- [ ] No errors in logs for 24 hours

**Integrations:**
- [ ] Works with Teslemetry
- [ ] Works with Amber Electric
- [ ] Works with alternative battery integrations (if supported)
- [ ] Works with alternative pricing sources (if supported)

**Edge Cases:**
- [ ] Handles sensor unavailable states
- [ ] Handles network disconnection
- [ ] Handles invalid modbus responses
- [ ] Handles threshold boundary conditions

## Documentation Updates

When making changes, update:

1. **README.md** - For user-facing changes
2. **docs/INSTALLATION.md** - For install procedure changes
3. **docs/INTEGRATIONS.md** - For new integration support
4. **docs/MODBUS_REGISTERS.md** - For register additions
5. **CHANGELOG.md** - For all changes
6. **examples/** - For new features needing examples

## Adding New Inverter Models

To add support for a new Sungrow model:

**1. Verify Modbus Compatibility**
- Test modbus connection
- Verify register addresses match
- Document any differences

**2. Update Configuration**
```yaml
# Add device type code to template
{% if state_val == 0x260F %}
  SG5.0RS
{% elif state_val == 0xYOUR_CODE %}
  SG6.0RS  # Add new model
{% endif %}
```

**3. Document Register Differences**
Update `docs/MODBUS_REGISTERS.md` with model-specific notes

**4. Update README**
Add to supported models list

**5. Test Thoroughly**
All features must work on new model

## Questions?

- Open a [Discussion](https://github.com/Artic0din/sungrow-sg5-price-curtailment/discussions)
- Check [existing Issues](https://github.com/Artic0din/sungrow-sg5-price-curtailment/issues)
- Review [documentation](docs/)

## Code of Conduct

- Be respectful and constructive
- Welcome newcomers
- Focus on improving the project
- No spam or off-topic content

## License

By contributing, you agree that your contributions will be licensed under the MIT License.

---

**Thank you for contributing! Every improvement helps the community.** ⭐
