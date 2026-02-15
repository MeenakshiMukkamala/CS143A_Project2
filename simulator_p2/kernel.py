### Fill in the following information before submitting
# Group id: 
# Members: Rishita Dugar, Alex Do, Pragya Jhunjhunwala, Meenakshi Mukkamala



from collections import deque

# PID is just an integer, but it is used to make it clear when a integer is expected to be a valid PID.
PID = int

# This class represents the PCB of processes.
# It is only here for your convinience and can be modified however you see fit.
class PCB:
    pid: PID
    priority: int
    process_type: str

    def __init__(self, pid: PID, priority: int = 0, process_type: str = "Foreground"):
        self.pid = pid
        self.priority = priority
        self.process_type = process_type


# This class represents the Kernel of the simulation.
# The simulator will create an instance of this object and use it to respond to syscalls and interrupts.
# DO NOT modify the name of this class or remove it.
class Kernel:
    scheduling_algorithm: str
    ready_queue: deque[PCB]
    waiting_queue: deque[PCB]
    running: PCB
    idle_pcb: PCB
    quantum_counter: int

    fg_queue: deque[PCB]
    bg_queue: deque[PCB]
    current_level: str
    level_counter: int

    # Called before the simulation begins.
    # Use this method to initilize any variables you need throughout the simulation.
    # logger is provided which allows you to include your own print statements in the
    #   output logs. These will not impact grading. This can be done with its .log method
    #   which accepts a string.
    # DO NOT rename or delete this method. DO NOT change its arguments.
    def __init__(self, scheduling_algorithm: str, logger):
        self.scheduling_algorithm = scheduling_algorithm
        self.ready_queue = deque()
        self.waiting_queue = deque()
        self.idle_pcb = PCB(0)
        self.running = self.idle_pcb
        self.quantum_counter = 0
        self.RR_QUANTUM_TICKS = 4
        self.logger = logger

        # For Multilevel
        self.fg_queue = deque()
        self.bg_queue = deque()
        self.current_level = "Foreground"
        self.level_counter = 0
        self.level_ticks = 0
        self.LEVEL_COMMIT_TICKS = 20

    #Helper functions for Multilevel
    def _level_has_work(self, level: str) -> bool:
        if level == "Foreground":
            in_queue = len(self.fg_queue) > 0
            running_matches = (self.running is not self.idle_pcb and self.running.process_type == "Foreground")
            return in_queue or running_matches
        else:
            in_queue = len(self.bg_queue) > 0
            running_matches = (self.running is not self.idle_pcb and self.running.process_type == "Background")
            return in_queue or running_matches

    def _other_level(self) -> str:
        return "Background" if self.current_level == "Foreground" else "Foreground"

    def _enqueue_preempted_running(self):
        if self.running is self.idle_pcb:
            return
        if self.running.process_type == "Foreground":
            self.fg_queue.append(self.running)
            self.quantum_counter = 0
        else:
            self.bg_queue.appendleft(self.running)

        self.running = self.idle_pcb

    def _switch_level_if_possible(self) -> bool:
        other = self._other_level()
        if not self._level_has_work(other):
            self.level_ticks = 0
            return False

        self.current_level = other
        self.level_ticks = 0

        if self.current_level == "Foreground":
            self.quantum_counter = 0

        return True

    def _pick_next_multilevel(self):
        if self.running is not self.idle_pcb:
            return

        if self.current_level == "Foreground":
            if len(self.fg_queue) > 0:
                self.running = self.fg_queue.popleft()
                self.quantum_counter = 0
                return

            if len(self.bg_queue) > 0:
                self.current_level = "Background"
                self.level_ticks = 0
                self.running = self.bg_queue.popleft()
                return

        else:
            if len(self.bg_queue) > 0:
                self.running = self.bg_queue.popleft()
                return

            if len(self.fg_queue) > 0:
                self.current_level = "Foreground"
                self.level_ticks = 0
                self.quantum_counter = 0
                self.running = self.fg_queue.popleft()
                return


    # This method is triggered every time a new process has arrived.
    # new_process is this process's PID.
    # DO NOT rename or delete this method. DO NOT change its arguments.
    def new_process_arrived(self, new_process: PID, priority: int, process_type: str) -> PID:
        pcb = PCB(new_process, priority=priority, process_type=process_type)

        if self.scheduling_algorithm == "Multilevel":
            if process_type == "Foreground":
                self.fg_queue.append(pcb)
            else:
                self.bg_queue.append(pcb)

            self._pick_next_multilevel()
            return self.running.pid
        
        #Original behavior if not Multilevel
        self.ready_queue.append(pcb)
        self.choose_next_process()
        return self.running.pid  

    # This method is triggered every time the current process performs an exit syscall.
    # DO NOT rename or delete this method. DO NOT change its arguments.
    def syscall_exit(self) -> PID:
        self.running = self.idle_pcb

        if self.scheduling_algorithm == "Multilevel":
            self._pick_next_multilevel()
            return self.running.pid

        self.choose_next_process()
        return self.running.pid
    
    # This method is triggered when the currently running process requests to change its priority.
    # DO NOT rename or delete this method. DO NOT change its arguments.
    def syscall_set_priority(self, new_priority: int) -> PID:
        if self.running is not self.idle_pcb:
            self.running.priority = new_priority

        if self.scheduling_algorithm == "Multilevel":
            self._pick_next_multilevel()
            return self.running.pid

        self.choose_next_process()
        return self.running.pid

    # This method represents the hardware timer interrupt.
    # It is triggered every 10 milliseconds and is the only way our kernel can track passing time.
    # Do not use real time to track how much time has passed as time is simulated.
    # DO NOT rename or delete this method. DO NOT change its arguments.
    def timer_interrupt(self) -> PID:
        if self.scheduling_algorithm == "Multilevel":
            self.level_ticks += 1

        if self.current_level == "Foreground":
            fg_running = (self.running is not self.idle_pcb and self.running.process_type == "Foreground")
            if (not fg_running) and len(self.fg_queue) == 0:
                self._switch_level_if_possible()
                self._pick_next_multilevel()
                return self.running.pid
        else:
            bg_running = (self.running is not self.idle_pcb and self.running.process_type == "Background")
            if (not bg_running) and len(self.bg_queue) == 0:
                self._switch_level_if_possible()
                self._pick_next_multilevel()
                return self.running.pid

        if self.level_ticks >= self.LEVEL_COMMIT_TICKS:
            self._enqueue_preempted_running()
            self._switch_level_if_possible()
            self._pick_next_multilevel()

            return self.running.pid

        if self.current_level == "Foreground":
            if self.running is not self.idle_pcb and self.running.process_type == "Foreground":
                self.quantum_counter += 1

                if self.quantum_counter >= self.RR_QUANTUM_TICKS:
                    if len(self.fg_queue) > 0:
                        self.fg_queue.append(self.running)
                        self.running = self.fg_queue.popleft()
                    self.quantum_counter = 0
            else:
                self.quantum_counter = 0

        return self.running.pid

        # RR timer
        self.quantum_counter += 1
        if self.scheduling_algorithm == "RR" and self.quantum_counter == 4 and len(self.ready_queue) > 0:
            if self.running is not self.idle_pcb:
                self.ready_queue.append(self.running)
            self.running = self.ready_queue.popleft()
            self.quantum_counter = 0

        return self.running.pid
    
    # This is where you can select the next process to run.
    # This method is not directly called by the simulator and is purely for your convinience.
    # Feel free to modify this method as you see fit.
    # It is not required to actually use this method but it is recommended.
    def choose_next_process(self):
        if len(self.ready_queue) == 0:
                return
        if self.scheduling_algorithm == "FCFS":
            if self.running is self.idle_pcb:
                self.running = self.ready_queue.popleft()
        elif self.scheduling_algorithm == "RR":
            if self.running is self.idle_pcb:
                self.running = self.ready_queue.popleft()
                self.quantum_counter = 0
        else:
            print("Unknown scheduling algorithm")
