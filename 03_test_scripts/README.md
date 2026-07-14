

## 目录内容

- `function_test.py`：纯逻辑功能测试，不依赖服务端启动。
- `boundary_test.py`：边界与异常测试，需要服务端先启动。
- `load_test.py`：并发压力测试，需要服务端先启动。
- `performance_test.py`：性能指标测试，需要服务端先启动。
- `test_support.py`：测试公共工具，负责定位 `01_source_code` 并封装协议收发。

## 运行方式

先进入源码根目录或测试目录均可，下面两种方式都支持。

```bash
python submission_package/03_test_scripts/function_test.py
python submission_package/03_test_scripts/boundary_test.py
python submission_package/03_test_scripts/load_test.py -n 50
python submission_package/03_test_scripts/performance_test.py
```

或：

```bash
cd submission_package/03_test_scripts
python function_test.py
python boundary_test.py
python load_test.py -n 50
python performance_test.py
```

## 运行前提

- `function_test.py` 可直接运行。
- 其余 3 个脚本会连接聊天服务器，运行前请先启动：

```bash
python ../01_source_code/server/server.py
```

如果在不同电脑上测试，请确认 `../01_source_code/common/config.py` 中的 `SERVER_HOST` 已改成服务端电脑的局域网 IP。
