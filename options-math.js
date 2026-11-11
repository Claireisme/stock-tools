(function (root, factory) {
  const api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  else root.OptionsMath = api;
})(typeof globalThis !== 'undefined' ? globalThis : this, function () {
  'use strict';

  function number(value, name, minimum) {
    if (value === '' || value === null || value === undefined || !Number.isFinite(Number(value))) throw new Error(`${name} must be a finite number`);
    const result = Number(value);
    if (minimum !== undefined && result < minimum) throw new Error(`${name} must be at least ${minimum}`);
    return result;
  }

  function day(value) {
    if (typeof value !== 'string' || !/^\d{4}-\d{2}-\d{2}$/.test(value)) throw new Error('Invalid date');
    const timestamp = Date.parse(`${value}T00:00:00Z`);
    if (!Number.isFinite(timestamp) || new Date(timestamp).toISOString().slice(0, 10) !== value) throw new Error('Invalid date');
    return timestamp;
  }

  function normalCDF(x) {
    const a = Math.abs(x), t = 1 / (1 + 0.2316419 * a);
    const tail = Math.exp(-a * a / 2) / Math.sqrt(2 * Math.PI) * t * (0.319381530 + t * (-0.356563782 + t * (1.781477937 + t * (-1.821255978 + t * 1.330274429))));
    return x >= 0 ? 1 - tail : tail;
  }

  function price({ type, spot, strike, years, volatility, rate = 0, dividend = 0 }) {
    if (type !== 'call' && type !== 'put') throw new Error('Invalid option type');
    const s = number(spot, 'spot', 0), k = number(strike, 'strike', 0);
    const t = number(years, 'years', 0), v = number(volatility, 'volatility', 0);
    const r = number(rate, 'rate'), q = number(dividend, 'dividend');
    const discountedS = s * Math.exp(-q * t), discountedK = k * Math.exp(-r * t);
    if (t === 0 || v === 0 || s === 0 || k === 0) return type === 'call' ? Math.max(0, discountedS - discountedK) : Math.max(0, discountedK - discountedS);
    const d1 = (Math.log(s / k) + (r - q + v * v / 2) * t) / (v * Math.sqrt(t));
    const d2 = d1 - v * Math.sqrt(t);
    return Math.max(0, type === 'call' ? discountedS * normalCDF(d1) - discountedK * normalCDF(d2) : discountedK * normalCDF(-d2) - discountedS * normalCDF(-d1));
  }

  function checkedLegs(legs) {
    if (!Array.isArray(legs) || !legs.length) throw new Error('At least one option leg is required');
    return legs.map(leg => {
      if (leg.type !== 'call' && leg.type !== 'put') throw new Error('Invalid option type');
      if (leg.side !== 'buy' && leg.side !== 'sell') throw new Error('Invalid option side');
      const contracts = number(leg.contracts, 'contracts', 1);
      if (!Number.isInteger(contracts)) throw new Error('Contracts must be an integer');
      return { ...leg, strike: number(leg.strike, 'strike', 0), premium: number(leg.premium, 'premium', 0), contracts, multiplier: number(leg.multiplier === undefined ? 100 : leg.multiplier, 'multiplier', 1) };
    });
  }

  function profit({ legs, spot, date, rate = 0, dividend = 0, shares = 0, stockEntry = 0 }) {
    const s = number(spot, 'spot', 0), when = day(date);
    const stockShares = number(shares, 'shares'), entry = number(stockEntry, 'stockEntry', 0);
    let result = stockShares * (s - entry);
    for (const leg of checkedLegs(legs)) {
      const expiry = day(leg.expiry);
      if (when > expiry) throw new Error('Calculation date cannot be after a leg expires');
      const years = (expiry - when) / (365 * 86400000);
      const value = price({ type: leg.type, spot: s, strike: leg.strike, years, volatility: leg.volatility === undefined ? 0 : leg.volatility, rate, dividend });
      result += (leg.side === 'buy' ? 1 : -1) * (value - leg.premium) * leg.contracts * leg.multiplier;
    }
    if (!Number.isFinite(result)) throw new Error('Result is too large');
    return result;
  }

  function expiryAnalysis({ legs, shares = 0, stockEntry = 0 }) {
    const positions = checkedLegs(legs), stockShares = number(shares, 'shares'), entry = number(stockEntry, 'stockEntry', 0);
    const dates = positions.map(leg => leg.expiry);
    dates.forEach(day);
    if (dates.some(date => date !== dates[0])) throw new Error('All option legs must expire on the same date');
    const payoff = spot => positions.reduce((sum, leg) => {
      const intrinsic = leg.type === 'call' ? Math.max(0, spot - leg.strike) : Math.max(0, leg.strike - spot);
      return sum + (leg.side === 'buy' ? 1 : -1) * (intrinsic - leg.premium) * leg.contracts * leg.multiplier;
    }, stockShares * (spot - entry));
    const points = [...new Set([0, ...positions.map(leg => leg.strike)])].sort((a, b) => a - b);
    const values = points.map(payoff);
    const slope = positions.reduce((sum, leg) => sum + (leg.type === 'call' ? (leg.side === 'buy' ? 1 : -1) * leg.contracts * leg.multiplier : 0), stockShares);
    const roots = [], ranges = [], eps = 1e-8;
    const addRoot = x => { if (!roots.some(existing => Math.abs(existing - x) < eps)) roots.push(x); };
    for (let i = 0; i < points.length; i++) {
      if (Math.abs(values[i]) < eps) addRoot(points[i]);
      if (i < points.length - 1) {
        if (Math.abs(values[i]) < eps && Math.abs(values[i + 1]) < eps) ranges.push([points[i], points[i + 1]]);
        else if (values[i] * values[i + 1] < 0) addRoot(points[i] + (points[i + 1] - points[i]) * (-values[i]) / (values[i + 1] - values[i]));
      }
    }
    const last = points.length - 1;
    if (Math.abs(slope) < eps && Math.abs(values[last]) < eps) ranges.push([points[last], Infinity]);
    else if (Math.abs(slope) >= eps) {
      const root = points[last] - values[last] / slope;
      if (root > points[last] + eps) addRoot(root);
    }
    const max = slope > 0 ? Infinity : Math.max(...values);
    const min = slope < 0 ? -Infinity : Math.min(...values);
    return { breakevens: roots.sort((a, b) => a - b), breakevenRanges: ranges, maxProfit: max, maxLoss: Math.max(0, -min) };
  }

  return { price, profit, expiryAnalysis };
});
