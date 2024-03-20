import "other1.wdl" as other1
import "other2.wdl" as other2

workflow DemoWorkflow {

    String sA
    String sB

    call other1.task1 as t1 {
        input:
            s = sA
    }

    call other2.task2 as t2 {
        input:
            s = sB
    }

    output {

    }
}
