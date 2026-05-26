# Benchmark Macros (Fast Runs)

These macros are intended for runtime benchmarking with **small particle counts**.
All runs are configured for:

- gamma source
- quadratic detector section
- CeBr3 scintillator
- reflector enabled (type 0)
- housing disabled

Macro groups:

- `outputs_*.mac`: same geometry/source, different analysis outputs
- `size_*.mac`: same source/output, different scintillator XY size
- `particles_*.mac`: same source/geometry/output, different `/run/beamOn`
- `energy_*.mac`: same geometry/output/event count, different gamma energy

All files in this folder are ready to run with:

```bash
./scripts/run_batch.sh scripts/macros/benchmark/<macro_name>.mac
```
