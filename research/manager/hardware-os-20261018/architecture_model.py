"""Conditional latency intervals; no physical model or device measurement."""
from fractions import Fraction
from pathlib import Path
import hashlib
import itertools
import json


def number(value, name, zero=True):
    if isinstance(value, bool):
        raise ValueError(name)
    try:
        value = Fraction(str(value))
    except (ValueError, ZeroDivisionError) as exc:
        raise ValueError(name) from exc
    if value < 0 or (not zero and value == 0):
        raise ValueError(name)
    return value


def integer(value, name, zero=False):
    if type(value) is not int or value < (0 if zero else 1):
        raise ValueError(name)
    return value


def evaluate(config, cold, gpu_ms, cpu_ms, line_gbit_s, flows, rtt_ms):
    layers = integer(config['layers'], 'layers')
    cold = integer(cold, 'cold', zero=True)
    if cold > layers:
        raise ValueError('cold exceeds layers')
    hidden = integer(config['hidden'], 'hidden')
    intermediate = integer(config['intermediate'], 'intermediate')
    top_k = integer(config['top_k'], 'top_k')
    wb = number(config['weight_bytes'], 'weight bytes', zero=False)
    ab = number(config['activation_bytes'], 'activation bytes', zero=False)
    w = 3 * hidden * intermediate * top_k * wb
    a = 2 * hidden * ab
    efficiency = number(config['payload_efficiency'], 'efficiency', zero=False)
    if efficiency > 1:
        raise ValueError('efficiency exceeds one')
    net = number(line_gbit_s, 'line rate', zero=False) * 10**9 / 8 * efficiency / integer(flows, 'flows')
    pcie = number(config['pcie_gb_s'], 'PCIe', zero=False) * 10**9
    gpu = number(gpu_ms, 'GPU') / 1000
    cpu = number(cpu_ms, 'CPU') / 1000
    dense = number(config['dense_gpu_ms'], 'dense GPU') / 1000
    dense_cpu = number(config['dense_cpu_ms'], 'dense CPU') / 1000
    rtt = number(rtt_ms, 'RTT') / 1000
    base = layers * dense + (layers-cold) * gpu
    reference = layers * (dense + gpu)
    staging_lo = base + cold * (rtt + max(gpu, w/net, w/pcie))
    staging_hi = base + cold * (rtt + gpu + w/net + w/pcie)
    near_lo = base + cold * (rtt + max(cpu, a/net, a/pcie))
    near_hi = base + cold * (rtt + cpu + a/net + a/pcie)
    coarse = ((layers-cold)*(dense+gpu) + cold*(dense_cpu+cpu)
              + (rtt+a/net+a/pcie if cold else 0))
    reduction = number(config['min_latency_reduction'], 'threshold')
    if reduction > 1:
        raise ValueError('threshold exceeds one')
    if near_hi <= (1-reduction)*staging_lo and near_hi < staging_lo:
        decision = 'near_weights_robust_conditional'
    elif staging_hi <= (1-reduction)*near_lo and staging_hi < near_lo:
        decision = 'weight_staging_robust_conditional'
    else:
        decision = 'no_robust_20pct_winner'
    return {
        'cold_layers':cold, 'gpu_expert_ms':float(gpu*1000),
        'cpu_expert_ms':float(cpu*1000), 'line_gbit_s':float(line_gbit_s),
        'flows':flows, 'rtt_ms':float(rtt*1000),
        'payload_bytes_per_second':float(net),
        'selected_weight_bytes_per_cold_layer':int(w),
        'activation_roundtrip_bytes':int(a),
        'full_gpu_reference_ms_capacity_unverified':float(reference*1000),
        'weight_staging_lower_ms':float(staging_lo*1000),
        'weight_staging_serial_ms':float(staging_hi*1000),
        'near_weights_lower_ms':float(near_lo*1000),
        'near_weights_serial_ms':float(near_hi*1000),
        'coarse_layer_design_ms_feasibility_unverified':float(coarse*1000),
        'weight_staging_wire_bytes':int(cold*w),
        'near_weights_wire_bytes':int(cold*a),
        'coarse_layer_wire_bytes':int(a if cold else 0),
        'fine_grained_serial_roundtrips':cold,
        'coarse_serial_roundtrips':int(cold>0),
        'conditional_decision':decision,
        'inference_correctness':'unverified',
        'physical_performance':'not measured',
    }


def os_bound(fraction, removal):
    f = number(fraction, 'OS fraction')
    r = number(removal, 'removal')
    if f >= 1 or r > 1:
        raise ValueError('fractions out of range')
    reduction = f*r
    return {'assumed_removable_fraction':float(f), 'removed_fraction':float(r),
            'latency_reduction_fraction':float(reduction),
            'speedup_upper_bound':float(1/(1-reduction)),
            'meets_20pct_latency_gate': reduction >= Fraction(1,5)}


def run(config):
    rows = [evaluate(config, *values) for values in itertools.product(
        config['cold_layers'], config['gpu_expert_ms'], config['cpu_expert_ms'],
        config['line_gbit_s'], config['contending_flows'], config['rtt_ms'])]
    counts = {decision:sum(r['conditional_decision']==decision for r in rows)
              for decision in ('near_weights_robust_conditional',
                               'weight_staging_robust_conditional',
                               'no_robust_20pct_winner')}
    return {'scope':'assumed-input critical-path bounds; no measured inference',
            'case_count':len(rows), 'counts_not_probabilities':counts, 'rows':rows,
            'os_bounds':[os_bound(f,r) for f,r in itertools.product(
                config['removable_os_fractions'],config['removed_fractions'])]}


if __name__ == '__main__':
    source=Path(__file__).with_name('inputs.json').read_bytes()
    result=run(json.loads(source))
    result['input_sha256']=hashlib.sha256(source).hexdigest()
    print(json.dumps(result,indent=2,sort_keys=True))
