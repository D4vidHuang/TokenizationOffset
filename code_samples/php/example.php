<?php
/**
 * PHP示例文件
 * 展示了PHP的基本语法和特性
 */

// 打印标题
echo "PHP示例程序\n\n";

// 基本数据类型
$age = 30;
$salary = 10000.50;
$is_active = true;
$grade = 'A';

// 字符串
$name = "张三";

echo "基本数据:\n";
echo "姓名: $name\n";
echo "年龄: $age\n";
echo "薪资: $salary\n";
echo "是否活跃: " . ($is_active ? 'true' : 'false') . "\n";
echo "等级: $grade\n\n";

// 数组
$numbers = [1, 2, 3, 4, 5];
echo "数组元素:\n";
foreach ($numbers as $num) {
    echo "$num ";
}
echo "\n\n";

// 关联数组
$scores = [
    "数学" => 90,
    "语文" => 85,
    "英语" => 95
];

echo "成绩单:\n";
foreach ($scores as $subject => $score) {
    echo "$subject: $score\n";
}
echo "\n";

// 函数定义
function greet($name) {
    return "你好，$name！";
}

function add($a, $b) {
    return $a + $b;
}

// 带默认参数的函数
function calculate_salary($base, $bonus = 0, $tax_rate = 0.1) {
    return ($base + $bonus) * (1 - $tax_rate);
}

// 函数调用
echo greet($name) . "\n";
echo "5 + 3 = " . add(5, 3) . "\n";
echo "薪资计算: " . calculate_salary(10000, 2000) . "\n\n";

// 类定义
class Person {
    // 属性
    protected $name;
    protected $age;
    
    // 构造函数
    public function __construct($name, $age) {
        $this->name = $name;
        $this->age = $age;
    }
    
    // Getter方法
    public function getName() {
        return $this->name;
    }
    
    public function getAge() {
        return $this->age;
    }
    
    // 实例方法
    public function greet() {
        echo "你好，我是{$this->name}\n";
    }
    
    // 魔术方法
    public function __toString() {
        return "Person [name={$this->name}, age={$this->age}]";
    }
    
    // 静态方法
    public static function species() {
        return "人类";
    }
}

// 继承
class Employee extends Person {
    private $position;
    
    public function __construct($name, $age, $position) {
        parent::__construct($name, $age);
        $this->position = $position;
    }
    
    public function getPosition() {
        return $this->position;
    }
    
    // 覆盖父类方法
    public function greet() {
        echo "你好，我是{$this->name}，担任{$this->position}职位\n";
    }
    
    public function work() {
        echo "{$this->name}正在工作，职位是{$this->position}\n";
    }
    
    public function __toString() {
        return "Employee [name={$this->name}, age={$this->age}, position={$this->position}]";
    }
}

// 创建对象
echo "创建对象:\n";
$person = new Person("李四", 25);
echo $person . "\n";
$person->greet();
echo "类方法调用: " . Person::species() . "\n\n";

// 继承
echo "继承示例:\n";
$employee = new Employee("王五", 30, "开发工程师");
echo $employee . "\n";
$employee->greet();
$employee->work();
echo "\n";

// 接口
interface Workable {
    public function work();
    public function getSalary();
}

// 实现接口
class Manager extends Employee implements Workable {
    private $salary;
    
    public function __construct($name, $age, $salary) {
        parent::__construct($name, $age, "经理");
        $this->salary = $salary;
    }
    
    public function getSalary() {
        return $this->salary;
    }
}

// 使用接口
$manager = new Manager("赵六", 35, 20000);
echo "接口示例:\n";
$manager->greet();
$manager->work();
echo "薪资: " . $manager->getSalary() . "\n\n";

// 命名空间示例
namespace Utils {
    class Helper {
        public static function formatCurrency($amount) {
            return "¥" . number_format($amount, 2);
        }
    }
}

// 使用命名空间
echo "命名空间示例:\n";
echo "格式化货币: " . Utils\Helper::formatCurrency(1234.56) . "\n\n";

// 异常处理
echo "异常处理:\n";
try {
    $result = 10 / 0;
    echo "结果: $result\n";
} catch (DivisionByZeroError $e) {
    echo "捕获异常: " . $e->getMessage() . "\n";
} finally {
    echo "异常处理完成\n";
}
echo "\n";

// 匿名函数
$greeting = function($name) {
    return "你好，$name！";
};

echo "匿名函数: " . $greeting("小明") . "\n";

// 箭头函数 (PHP 7.4+)
$double = fn($x) => $x * 2;
echo "箭头函数: 5的两倍是" . $double(5) . "\n\n";

// 日期和时间
echo "日期和时间:\n";
$now = new DateTime();
echo "当前日期时间: " . $now->format('Y-m-d H:i:s') . "\n";
echo "时间戳: " . time() . "\n\n";

// JSON处理
$person_data = [
    'name' => '张三',
    'age' => 30,
    'skills' => ['PHP', 'JavaScript', 'MySQL']
];

$json = json_encode($person_data);
echo "JSON编码: $json\n";

$decoded = json_decode($json, true);
echo "JSON解码: 姓名 - " . $decoded['name'] . ", 技能 - " . implode(', ', $decoded['skills']) . "\n";

echo "\nPHP示例程序结束\n";
?>