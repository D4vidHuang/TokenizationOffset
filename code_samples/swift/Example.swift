/**
 * Swift示例文件
 * 展示了Swift的基本语法和特性
 */

import Foundation

// 打印标题
print("Swift示例程序\n")

// 基本数据类型
let age: Int = 30
let salary: Double = 10000.50
let isActive: Bool = true
let grade: Character = "A"

// 字符串
let name = "张三"

print("基本数据:")
print("姓名: \(name)")
print("年龄: \(age)")
print("薪资: \(salary)")
print("是否活跃: \(isActive)")
print("等级: \(grade)\n")

// 变量
var counter = 0
counter += 1
print("计数器: \(counter)\n")

// 数组
let numbers = [1, 2, 3, 4, 5]
print("数组元素:")
for num in numbers {
    print("\(num) ", terminator: "")
}
print("\n")

// 可变数组
var fruits = ["苹果", "香蕉", "橙子"]
print("水果列表:")
for fruit in fruits {
    print("- \(fruit)")
}

// 添加元素到数组
fruits.append("葡萄")
print("\n添加后的水果: \(fruits)\n")

// 字典
var scores = [
    "数学": 90,
    "语文": 85,
    "英语": 95
]

print("成绩单:")
for (subject, score) in scores {
    print("\(subject): \(score)")
}
print()

// 元组
let personInfo = (name: "李四", age: 25, city: "北京")
print("元组示例:")
print("姓名: \(personInfo.name)")
print("年龄: \(personInfo.age)")
print("城市: \(personInfo.city)\n")

// 函数定义
func greet(person: String) -> String {
    return "你好，\(person)！"
}

func add(a: Int, b: Int) -> Int {
    return a + b
}

// 带默认参数和标签的函数
func calculateSalary(base: Double, bonus: Double = 0, withTaxRate taxRate: Double = 0.1) -> Double {
    return (base + bonus) * (1 - taxRate)
}

// 函数调用
print(greet(person: name))
print("5 + 3 = \(add(a: 5, b: 3))")
print("薪资计算: \(calculateSalary(base: 10000, bonus: 2000))\n")

// 类定义
class Person {
    // 属性
    var name: String
    var age: Int
    
    // 计算属性
    var description: String {
        return "Person [name=\(name), age=\(age)]"
    }
    
    // 构造函数
    init(name: String, age: Int) {
        self.name = name
        self.age = age
    }
    
    // 实例方法
    func greet() {
        print("你好，我是\(name)")
    }
    
    // 类方法
    class func species() -> String {
        return "人类"
    }
}

// 继承
class Employee: Person {
    // 额外的属性
    var position: String
    
    // 构造函数
    init(name: String, age: Int, position: String) {
        self.position = position
        super.init(name: name, age: age)
    }
    
    // 覆盖计算属性
    override var description: String {
        return "Employee [name=\(name), age=\(age), position=\(position)]"
    }
    
    // 覆盖方法
    override func greet() {
        print("你好，我是\(name)，担任\(position)职位")
    }
    
    // 额外的方法
    func work() {
        print("\(name)正在工作，职位是\(position)")
    }
}

// 创建对象
print("创建对象:")
let person = Person(name: "王五", age: 30)
print(person.description)
person.greet()
print("类方法调用: \(Person.species())\n")

// 继承
print("继承示例:")
let employee = Employee(name: "赵六", age: 28, position: "开发工程师")
print(employee.description)
employee.greet()
employee.work()
print()

// 协议
protocol Worker {
    var position: String { get }
    func work()
    func getSalary() -> Double
}

// 实现协议
class Manager: Employee, Worker {
    private var salary: Double
    
    init(name: String, age: Int, salary: Double) {
        self.salary = salary
        super.init(name: name, age: age, position: "经理")
    }
    
    func getSalary() -> Double {
        return salary
    }
}

// 使用协议
let manager = Manager(name: "钱七", age: 35, salary: 20000)
print("协议示例:")
manager.greet()
manager.work()
print("薪资: \(manager.getSalary())\n")

// 枚举
enum Status {
    case active
    case inactive
    case pending
}

// 带关联值的枚举
enum Message {
    case quit
    case move(x: Int, y: Int)
    case write(String)
    case changeColor(r: Int, g: Int, b: Int)
}

// 使用枚举
let status = Status.active
print("枚举示例:")
switch status {
case .active:
    print("状态: 活跃")
case .inactive:
    print("状态: 不活跃")
case .pending:
    print("状态: 待定")
}

// 使用带关联值的枚举
let messages: [Message] = [
    .quit,
    .move(x: 10, y: 20),
    .write("你好，Swift!"),
    .changeColor(r: 255, g: 0, b: 0)
]

print("\n消息示例:")
for message in messages {
    switch message {
    case .quit:
        print("退出消息")
    case .move(let x, let y):
        print("移动到坐标: (\(x), \(y))")
    case .write(let text):
        print("文本消息: \(text)")
    case .changeColor(let r, let g, let b):
        print("颜色变更为: RGB(\(r), \(g), \(b))")
    }
}
print()

// 可选类型
var optionalName: String? = "可选字符串"
var optionalNumber: Int? = nil

print("可选类型示例:")
if let name = optionalName {
    print("可选名称: \(name)")
}

if let number = optionalNumber {
    print("可选数字: \(number)")
} else {
    print("可选数字为nil")
}

// 使用guard语句
func processOptional(value: String?) {
    guard let unwrapped = value else {
        print("值为nil")
        return
    }
    print("解包后的值: \(unwrapped)")
}

processOptional(value: optionalName)
processOptional(value: nil)
print()

// 闭包
let addClosure = { (a: Int, b: Int) -> Int in
    return a + b
}

print("闭包示例:")
print("5 + 3 = \(addClosure(5, 3))")

// 尾随闭包
let numbers2 = [1, 2, 3, 4, 5]
let doubled = numbers2.map { $0 * 2 }
print("数字加倍: \(doubled)")

// 排序
let names = ["张三", "李四", "王五", "赵六"]
let sortedNames = names.sorted { $0.count < $1.count }
print("按长度排序的名字: \(sortedNames)\n")

// 结构体
struct Point {
    var x: Double
    var y: Double
    
    // 方法
    func distanceFromOrigin() -> Double {
        return sqrt(x*x + y*y)
    }
    
    // 变异方法
    mutating func moveBy(x deltaX: Double, y deltaY: Double) {
        x += deltaX
        y += deltaY
    }
}

print("结构体示例:")
var point = Point(x: 3, y: 4)
print("点: (\(point.x), \(point.y))")
print("到原点的距离: \(point.distanceFromOrigin())")
point.moveBy(x: 2, y: 3)
print("移动后: (\(point.x), \(point.y))\n")

// 扩展
extension String {
    func repeated(times: Int) -> String {
        return String(repeating: self, count: times)
    }
}

print("扩展示例:")
let star = "*"
print("\(star) 重复5次: \(star.repeated(times: 5))\n")

// 错误处理
enum MathError: Error {
    case divisionByZero
}

func divide(_ a: Double, by b: Double) throws -> Double {
    guard b != 0 else {
        throw MathError.divisionByZero
    }
    return a / b
}

print("错误处理示例:")
do {
    let result = try divide(10, by: 2)
    print("10 / 2 = \(result)")
    
    let errorResult = try divide(10, by: 0)
    print("10 / 0 = \(errorResult)")
} catch MathError.divisionByZero {
    print("错误: 除数不能为零")
} catch {
    print("未知错误: \(error)")
}
print()

// 泛型
func swapValues<T>(_ a: inout T, _ b: inout T) {
    let temp = a
    a = b
    b = temp
}

print("泛型示例:")
var x = 5, y = 10
print("交换前: x = \(x), y = \(y)")
swapValues(&x, &y)
print("交换后: x = \(x), y = \(y)")

var str1 = "你好", str2 = "世界"
print("交换前: str1 = \(str1), str2 = \(str2)")
swapValues(&str1, &str2)
print("交换后: str1 = \(str1), str2 = \(str2)\n")

print("Swift示例程序结束")