# Production Deployment Checklist

**Engine:** Enterprise Construction & Infrastructure Cost Intelligence Engine  
**Version:** v1  
**Status:** ✅ Ready for Production

---

## Pre-Deployment Checklist

### Code & Tests
- [x] All unit tests passing (65/65 tests)
- [x] Integration tests passing
- [x] Production readiness tests passing
- [x] Code reviewed and approved
- [x] No critical bugs or issues

### Documentation
- [x] README.md complete
- [x] API documentation complete
- [x] Deployment documentation complete
- [x] Verification reports complete

### Platform Integration
- [x] Engine registered in platform
- [x] FastAPI routes configured
- [x] Kill-switch tested and operational
- [x] Engine can be enabled/disabled safely

### Data & Traceability
- [x] Finding persistence implemented
- [x] Evidence linkage verified
- [x] DatasetVersion binding verified
- [x] DatasetVersion isolation verified

---

## Deployment Steps

### Step 1: Pre-Deployment Verification
```bash
# Run all tests
pytest backend/tests/engine_construction_cost_intelligence/ -v

# Verify engine registration
python3 -c "from backend.app.engines import register_all_engines; register_all_engines(); from backend.app.core.engine_registry.registry import REGISTRY; print(REGISTRY.get('engine_construction_cost_intelligence'))"
```

### Step 2: Environment Configuration
```bash
# Set environment variable (production)
export TODISCOPE_ENABLED_ENGINES=engine_construction_cost_intelligence

# Or add to existing engines
export TODISCOPE_ENABLED_ENGINES="engine_construction_cost_intelligence,engine_csrd"
```

### Step 3: Application Restart
```bash
# Restart application to load engine
# Engine will automatically:
# - Register with platform
# - Mount routes
# - Enable kill-switch checks
```

### Step 4: Post-Deployment Verification
```bash
# Verify engine is accessible
curl http://api/v3/engines/cost-intelligence/ping

# Expected response:
# {"ok": true, "engine_id": "engine_construction_cost_intelligence", "engine_version": "v1"}
```

---

## Rollback Procedure

### Instant Disable (Kill-Switch)
```bash
# Remove engine from enabled list
export TODISCOPE_ENABLED_ENGINES=""  # or remove from comma-separated list

# Restart application
# Engine will be immediately disabled
# Routes will return 503
# No data loss or corruption
```

### Zero-Downtime Rollback
1. Remove engine from `TODISCOPE_ENABLED_ENGINES`
2. Restart application
3. Engine routes automatically unmounted
4. Platform continues to function normally

---

## Monitoring Checklist

### Immediate Post-Deployment
- [ ] Verify `/ping` endpoint responds
- [ ] Check application logs for errors
- [ ] Verify engine registered in platform
- [ ] Test one engine run with sample data

### First 24 Hours
- [ ] Monitor error rates
- [ ] Check performance metrics
- [ ] Verify findings persistence
- [ ] Verify evidence linkage
- [ ] Check database load

### First Week
- [ ] Review all findings created
- [ ] Verify DatasetVersion isolation
- [ ] Check evidence traceability
- [ ] Review performance trends

---

## Support & Troubleshooting

### Common Issues

**Issue:** Engine returns 503
- **Solution:** Verify `TODISCOPE_ENABLED_ENGINES` includes engine ID

**Issue:** Routes return 404
- **Solution:** Verify engine is registered and application restarted

**Issue:** Findings not persisted
- **Solution:** Verify `persist_findings=True` in report parameters

**Issue:** Evidence not linked
- **Solution:** Verify `emit_evidence=True` in report parameters

### Contact

For deployment issues, contact:
- Engineering Team
- Platform Team
- Database Team (for DatasetVersion/evidence issues)

---

## Deployment Sign-Off

**Prepared by:** Deployment Engineer  
**Date:** 2025-01-XX  
**Status:** ✅ Ready for Production Deployment

**Approvals:**
- [ ] Engineering Lead
- [ ] QA Lead
- [ ] Platform Lead
- [ ] Product Owner






