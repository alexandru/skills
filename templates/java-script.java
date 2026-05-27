///usr/bin/env jbang "$0" "$@" ; exit $?

//JAVA 17+

import java.util.random.RandomGenerator;

class JavaScriptTemplate {
    public static void main(String[] args) {
        var name = args.length > 0 ? args[0] : "World";
        var suffix = RandomGenerator.getDefault().nextInt(1_000);

        System.out.println("Hello, " + name + " (#" + suffix + ")");
    }
}
