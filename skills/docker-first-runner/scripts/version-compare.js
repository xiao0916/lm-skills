// 解析版本字符串为对象
const parseVersion = (v) => {
  const m = v.match(/(\d+)\.(\d+)\.(\d+)/);
  if (!m) return null;
  const major = parseInt(m[1], 10);
  const minor = parseInt(m[2], 10);
  const patch = parseInt(m[3], 10);
  const prerelease = /-(?:rc|alpha|beta)\d*|p\d+/.test(v);
  return { major, minor, patch, prerelease };
};

// 比较两个版本，如果 v1 >= v2 返回 true
const compareVersions = (v1, v2) => {
  const a = parseVersion(v1);
  const b = parseVersion(v2);
  if (!a || !b) return false;
  if (a.major !== b.major) return a.major > b.major;
  if (a.minor !== b.minor) return a.minor > b.minor;
  if (a.patch !== b.patch) return a.patch > b.patch;
  if (a.prerelease && !b.prerelease) return false;
  return true;
};

// 执行比较并输出结果
const result = compareVersions(process.argv[2], process.argv[3]);
console.log(result ? "true" : "false");
process.exit(result ? 0 : 1);
